"""OSINT companies — domain guess + validation + crt.sh subdomain discovery.

Target: bronze.osint_companies (enriches top-capital SAS/SA/SCA with web domains).
Pure Python (no docker-in-docker needed).
"""
from __future__ import annotations

import json
import logging
import re
import socket
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime

import psycopg
from psycopg.types.json import Jsonb

from config import settings

log = logging.getLogger(__name__)

# Throttle per run (scheduler cadence handles frequency — keep each run bounded)
BATCH_SIZE = 100


def _slug_domain(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    for suf in (" SAS", " SA", " SARL", " SCA", " SNC", " EURL", " SCS", " SCI",
                " GROUP", " GROUPE", " HOLDING", " INVEST", " FRANCE"):
        if s.upper().endswith(suf):
            s = s[: -len(suf)]
    s = re.sub(r"[^a-zA-Z0-9]+", "", s).lower()
    return s[:30]


def _guess_domains(denomination, nom_commercial=None) -> list[str]:
    candidates: set[str] = set()
    for src in filter(None, (denomination, nom_commercial)):
        slug = _slug_domain(src)
        if not slug or len(slug) < 3:
            continue
        for tld in (".fr", ".com"):
            candidates.add(slug + tld)
        slug_hy = re.sub(r"[^a-zA-Z0-9]+", "-",
                         unicodedata.normalize("NFKD", src)
                         .encode("ASCII", "ignore").decode()).strip("-").lower()
        if slug_hy and slug_hy != slug:
            for tld in (".fr", ".com"):
                candidates.add(slug_hy[:40] + tld)
    return list(candidates)[:6]


def _probe_domain(domain: str, timeout: int = 5) -> bool:
    try:
        socket.gethostbyname(domain)
    except (socket.gaierror, socket.timeout):
        return False
    try:
        req = urllib.request.Request(f"https://{domain}", method="HEAD",
                                      headers={"User-Agent": "DEMOEMA-OSINT/0.1"})
        urllib.request.urlopen(req, timeout=timeout)
    except Exception:
        pass  # DNS resolves → still count as valid (some sites block HEAD)
    return True


def _crt_sh_subdomains(domain: str, timeout: int = 20) -> list[str]:
    try:
        url = f"https://crt.sh/?q=%25.{urllib.parse.quote(domain)}&output=json"
        req = urllib.request.Request(url, headers={"User-Agent": "DEMOEMA-OSINT/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", errors="ignore"))
        names = set()
        for row in data[:500]:
            for n in (row.get("name_value") or "").split("\n"):
                n = n.strip().lower().lstrip("*.")
                if n and (n == domain or n.endswith("." + domain)):
                    names.add(n)
        return sorted(names)[:200]
    except Exception:
        return []


PICK_SQL = """
SELECT siren, denomination, nom_commercial
FROM bronze.inpi_formalites_entreprises
WHERE forme_juridique IN ('5710','5720','5730','5485','5499','5505','5510','5515','5520','5530','5540','5599',
                          '5385','5308','5306','5202','5203')
  AND COALESCE(montant_capital, 0) >= 500000
  AND denomination IS NOT NULL
  AND siren NOT IN (SELECT siren FROM bronze.osint_companies WHERE last_scanned_at > now() - interval '90 days')
ORDER BY montant_capital DESC NULLS LAST
LIMIT %s
"""

UPSERT_SQL = """
INSERT INTO bronze.osint_companies
  (siren, domains, subdomains_crt_sh, sources_scanned, last_scanned_at, payload)
VALUES (%s, %s, %s, %s, now(), %s)
ON CONFLICT (siren) DO UPDATE SET
  domains = EXCLUDED.domains,
  subdomains_crt_sh = EXCLUDED.subdomains_crt_sh,
  last_scanned_at = now(),
  payload = EXCLUDED.payload
"""


async def fetch_osint_companies_delta() -> dict:
    if not settings.database_url:
        return {"source": "osint_companies", "rows": 0, "error": "no DB"}

    t0 = time.time()
    n_scanned = n_with_domain = total_subdomains = 0

    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor() as cur:
            await cur.execute(PICK_SQL, (BATCH_SIZE,))
            rows = await cur.fetchall()

        for (siren, denom, nomcom) in rows:
            candidates = _guess_domains(denom, nomcom)
            validated = [d for d in candidates if _probe_domain(d)]
            subdomains: list[str] = []
            for d in validated[:3]:
                subdomains.extend(_crt_sh_subdomains(d))
            subdomains = sorted(set(subdomains))[:500]

            payload = {
                "candidates_tried": candidates,
                "denomination": denom,
                "scanned_at": datetime.utcnow().isoformat(),
            }

            async with conn.cursor() as ucur:
                await ucur.execute(UPSERT_SQL, (
                    siren,
                    validated or None,
                    subdomains or None,
                    ["domain_guess", "crt_sh"],
                    Jsonb(payload),
                ))
            await conn.commit()

            n_scanned += 1
            if validated:
                n_with_domain += 1
            total_subdomains += len(subdomains)

    return {
        "source": "osint_companies",
        "rows": n_scanned,
        "with_domain": n_with_domain,
        "total_subdomains": total_subdomains,
        "duration_s": round(time.time() - t0, 1),
    }
