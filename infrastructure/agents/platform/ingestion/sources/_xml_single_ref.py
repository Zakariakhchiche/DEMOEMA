"""RÉFÉRENCE XML-SINGLE — pattern pour sources livrant UN gros fichier XML.

CE FICHIER N'EST PAS EXECUTE — il sert de modèle au codegen pour générer des
fetchers de type "URL HTTP renvoie un seul XML, possiblement 10-500 MB,
contenant N records sous une racine".

Exemples typiques :
- EU sanctions (consolidated list XML)
- OFAC SDN.xml
- World Bank XML datasets
- INSEE NAF XML

Pattern clé :
  1. httpx.AsyncClient().stream("GET", url) → download bytes
  2. lxml.etree.iterparse(BytesIO(data), events=('end',), tag=RECORD_TAG)
     → streaming parse (ne charge pas tout l'arbre en RAM)
  3. À chaque element matched : extract record_id via xpath relatif
     + build payload dict (tag → text concat)
  4. Batch INSERT ... ON CONFLICT (key) DO UPDATE
  5. element.clear() + iter parent.clear() après chaque parse pour libérer la RAM

⚠️ Pour les gros XML (>100 MB), iterparse + element.clear() est OBLIGATOIRE,
sinon l'arbre lxml entier reste en RAM (~10x la taille du fichier).

Variables clés :
- ENDPOINT_URL : URL du XML
- RECORD_TAG : tag XML à matcher pour itération
- XPATH_ID : xpath relatif depuis le record pour extraire l'ID
- TABLE_NAME, KEY_COLUMN
- BATCH_SIZE, MAX_ROWS
"""
from __future__ import annotations

import hashlib
import io
import logging
from datetime import datetime, timezone

import httpx
import psycopg
from psycopg.types.json import Jsonb
from lxml import etree

from config import settings

log = logging.getLogger(__name__)

# À SURCHARGER
ENDPOINT_URL = "https://example.gouv.fr/data/dataset.xml"
RECORD_TAG = "Record"
XPATH_ID = ".//Id"
TABLE_NAME = "bronze.example_raw"
KEY_COLUMN = "record_id"
BATCH_SIZE = 1000
MAX_ROWS = 500_000
NAMESPACE = ""  # Si XML namespacé : "{http://example.org/ns}"


async def count_upstream() -> int | None:
    """Pas de count direct — XML doit être streamé. Retourner None est OK."""
    return None


def _record_to_tuple(elem: etree._Element, namespace: str = "") -> tuple | None:
    """Extract record_id + payload depuis un élément XML record."""
    record_id = None
    try:
        el = elem.find(XPATH_ID)
        if el is not None and el.text:
            record_id = el.text.strip()
    except Exception:
        pass
    if not record_id:
        # Fallback : sérialise le record + hash
        record_id = hashlib.sha1(etree.tostring(elem)).hexdigest()[:32]
    record_id = record_id[:128]

    payload = {"_root_tag": elem.tag.replace(namespace, "")}
    for child in elem:
        tag_clean = child.tag.replace(namespace, "")
        text = "".join(child.itertext()).strip()
        if text:
            payload[tag_clean] = text[:8000]

    return (record_id, Jsonb(payload), datetime.now(tz=timezone.utc))


async def fetch_example_delta() -> dict:
    """Stream download + iterparse + batch insert avec element.clear()."""
    if not settings.database_url:
        return {"source": "example", "rows": 0, "error": "no DB"}

    log.info("[example] downloading XML from %s", ENDPOINT_URL)
    async with httpx.AsyncClient(timeout=3600, follow_redirects=True,
                                  headers={"User-Agent": "DEMOEMA-Agents/0.1"}) as client:
        try:
            r = await client.get(ENDPOINT_URL)
        except Exception as e:
            return {"source": "example", "rows": 0, "error": f"download: {e}"}
        if r.status_code != 200:
            return {"source": "example", "rows": 0,
                    "error": f"HTTP {r.status_code}"}
        xml_bytes = r.content

    n_processed = 0
    n_inserted = 0

    # iterparse streaming — RAM-safe pour gros XML
    record_tag = f"{NAMESPACE}{RECORD_TAG}" if NAMESPACE else RECORD_TAG
    context = etree.iterparse(io.BytesIO(xml_bytes), events=("end",), tag=record_tag)

    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            batch = []
            for _, elem in context:
                if MAX_ROWS and n_processed >= MAX_ROWS:
                    break
                record = _record_to_tuple(elem, NAMESPACE)
                if record is not None:
                    batch.append(record)
                    n_processed += 1

                # CRITICAL : libérer la RAM après chaque element
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

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

    return {
        "source": "example",
        "rows": n_inserted,
        "processed": n_processed,
        "mode": "xml_single",
    }
