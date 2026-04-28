"""RÉFÉRENCE TAR.GZ-XML — pattern pour sources livrées en .tar.gz contenant des XML.

CE FICHIER N'EST PAS EXECUTE — il sert de modèle au codegen (lead-data-engineer)
pour générer des fetchers de type "index HTTP listant des .tar.gz, chaque archive
contient N fichiers XML, un par enregistrement".

Exemples typiques :
- DILA OpenData (CASS, CAPP, JADE, CONSTIT, JORF, LEGI, KALI)
- EU TED (avis de marchés publics européens)
- Eurostat bulk dumps XML
- BIS / OFAC consolidated lists XML

Pattern clé :
  1. GET sur INDEX_URL → HTML directory listing
  2. Regex sur le HTML pour extraire les noms des .tar.gz (BULK_URL_PATTERN)
  3. Trier (alphabétique inverse pour récents d'abord) + limiter (MAX_ARCHIVES)
  4. Pour chaque archive en parallèle (asyncio.Semaphore=4) :
     - download bytes via httpx.get
     - tarfile.open(fileobj=BytesIO(data), mode="r:gz") → itère les members
     - filter par XML_MEMBER_PATTERN (ex: '\\.xml$')
     - lxml.etree.fromstring(member_bytes) → extract record_id via XML_XPATH_ID
     - Build payload dict avec {tag: text} de chaque enfant direct
     - Batch INSERT ... ON CONFLICT (key) DO UPDATE (idempotent)
  5. Commit batch après chaque archive

Variables clés à customiser dans le fetcher concret :
- INDEX_URL : URL du listing HTTP
- BULK_URL_PATTERN : regex matching les noms d'archives
- XML_MEMBER_PATTERN : regex matching XML files in archive (default '\\.xml$')
- XML_XPATH_ID : xpath de l'ID dans le XML
- TABLE_NAME, KEY_COLUMN
- BATCH_SIZE, MAX_ARCHIVES, MAX_ROWS

⚠️ ARCHIVES LOURDES : chaque .tar.gz peut faire 50-500 MB → préfère 4 archives en
parallèle au max (Semaphore) plutôt que la totalité sinon RAM blow-up.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import re
import tarfile
from datetime import datetime, timezone
from urllib.parse import urljoin

import httpx
import psycopg
from psycopg.types.json import Jsonb
from lxml import etree

from config import settings

log = logging.getLogger(__name__)

# À SURCHARGER dans le fetcher concret
INDEX_URL = "https://echanges.dila.gouv.fr/OPENDATA/JADE/"
BULK_URL_PATTERN = r"JADE_\d{8}-\d{6}\.tar\.gz"
XML_MEMBER_PATTERN = r"\.xml$"
XML_XPATH_ID = ".//META_COMMUN/ID"
TABLE_NAME = "bronze.juri_jade_raw"
KEY_COLUMN = "decision_id"
BATCH_SIZE = 500
MAX_ARCHIVES = 100
MAX_ROWS = 1_000_000
ARCHIVE_PARALLELISM = 4


async def count_upstream() -> int | None:
    """Nombre d'archives discoverable (proxy de couverture)."""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
            r = await c.get(INDEX_URL)
            if r.status_code != 200:
                return None
            return len(set(re.findall(BULK_URL_PATTERN, r.text)))
    except Exception:
        return None


def _xml_to_record(xml_bytes: bytes, archive_name: str, member_name: str) -> tuple | None:
    """Parse 1 XML → (record_id, payload_jsonb, ingested_at). None si parse fail.

    record_id : extraction via xpath fourni → fallback xpath communs → SHA1 du contenu.
    payload : dict des tags directs avec leur text concaténé (limit 8K chars/champ).
    """
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError:
        return None

    record_id = None
    if XML_XPATH_ID:
        try:
            el = root.find(XML_XPATH_ID)
            if el is not None and el.text:
                record_id = el.text.strip()
        except Exception:
            pass
    if not record_id:
        for xp in (".//ID", ".//Id", ".//id", ".//Identifier", ".//identifier"):
            el = root.find(xp)
            if el is not None and el.text:
                record_id = el.text.strip()
                break
    if not record_id:
        record_id = hashlib.sha1(xml_bytes).hexdigest()[:32]
    record_id = record_id[:128]

    payload = {
        "_root_tag": root.tag,
        "_archive": archive_name,
        "_member": member_name,
    }
    for child in root:
        text = "".join(child.itertext()).strip()
        if text:
            payload[child.tag] = text[:8000]

    return (record_id, Jsonb(payload), datetime.now(tz=timezone.utc))


async def _ingest_archive(client: httpx.AsyncClient, archive_url: str) -> dict:
    """Download UNE archive, itère XML members, INSERT en batch."""
    archive_name = archive_url.rsplit("/", 1)[-1]
    log.info("[example] downloading %s", archive_name)

    try:
        r = await client.get(archive_url)
    except Exception as e:
        return {"archive": archive_name, "rows": 0, "error": f"download: {e}"}
    if r.status_code != 200:
        return {"archive": archive_name, "rows": 0, "error": f"HTTP {r.status_code}"}

    try:
        tar = tarfile.open(fileobj=io.BytesIO(r.content), mode="r:gz")
    except Exception as e:
        return {"archive": archive_name, "rows": 0, "error": f"tar: {e}"}

    member_re = re.compile(XML_MEMBER_PATTERN)
    n_processed = 0
    n_inserted = 0

    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            batch = []
            for member in tar:
                if not member.isreg() or not member_re.search(member.name):
                    continue
                if MAX_ROWS and n_processed >= MAX_ROWS:
                    break
                try:
                    fh = tar.extractfile(member)
                    if fh is None:
                        continue
                    record = _xml_to_record(fh.read(), archive_name, member.name)
                except Exception:
                    continue
                if record is None:
                    continue
                batch.append(record)
                n_processed += 1

                if len(batch) >= BATCH_SIZE:
                    try:
                        await cur.executemany(
                            f"INSERT INTO {TABLE_NAME} ({KEY_COLUMN}, payload, ingested_at) "
                            f"VALUES (%s, %s, %s) "
                            f"ON CONFLICT ({KEY_COLUMN}) DO UPDATE "
                            f"SET payload = EXCLUDED.payload, ingested_at = now()",
                            batch,
                        )
                        n_inserted += cur.rowcount or 0
                        await conn.commit()
                    except Exception as e:
                        log.warning("batch fail: %s", str(e)[:120])
                    batch.clear()

            if batch:
                try:
                    await cur.executemany(
                        f"INSERT INTO {TABLE_NAME} ({KEY_COLUMN}, payload, ingested_at) "
                        f"VALUES (%s, %s, %s) "
                        f"ON CONFLICT ({KEY_COLUMN}) DO UPDATE "
                        f"SET payload = EXCLUDED.payload, ingested_at = now()",
                        batch,
                    )
                    n_inserted += cur.rowcount or 0
                    await conn.commit()
                except Exception as e:
                    log.warning("final batch fail: %s", str(e)[:120])

    tar.close()
    return {"archive": archive_name, "rows": n_inserted, "processed": n_processed}


async def fetch_example_delta() -> dict:
    """Discover archives via INDEX_URL → ingest in parallel (Semaphore=4)."""
    if not settings.database_url:
        return {"source": "example", "rows": 0, "error": "no DB"}

    async with httpx.AsyncClient(timeout=3600, follow_redirects=True,
                                  headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        try:
            r = await client.get(INDEX_URL)
        except Exception as e:
            return {"source": "example", "rows": 0, "error": f"index: {e}"}
        if r.status_code != 200:
            return {"source": "example", "rows": 0,
                    "error": f"index HTTP {r.status_code}"}

        names = sorted(set(re.findall(BULK_URL_PATTERN, r.text)))
        if not names:
            return {"source": "example", "rows": 0,
                    "error": f"no archives matched {BULK_URL_PATTERN}"}

        if MAX_ARCHIVES and MAX_ARCHIVES > 0:
            names = sorted(names, reverse=True)[:MAX_ARCHIVES]
        urls = [urljoin(INDEX_URL.rstrip("/") + "/", n) for n in names]
        log.info("[example] %d archives, ingesting", len(urls))

        sem = asyncio.Semaphore(ARCHIVE_PARALLELISM)

        async def _one(url):
            async with sem:
                return await _ingest_archive(client, url)

        results = await asyncio.gather(*[_one(u) for u in urls], return_exceptions=True)

    total_rows = sum(r.get("rows", 0) for r in results if isinstance(r, dict))
    archives_failed = sum(
        1 for r in results
        if isinstance(r, dict) and "error" in r or isinstance(r, Exception)
    )

    return {
        "source": "example",
        "rows": total_rows,
        "archives_processed": len(urls),
        "archives_failed": archives_failed,
        "mode": "tar_gz_xml",
    }
