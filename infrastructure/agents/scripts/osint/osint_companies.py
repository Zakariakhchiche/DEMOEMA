#!/usr/bin/env python3
"""OSINT companies — domain guess + validation + crt.sh subdomains + RDAP.

For each SIREN: guess common domain forms from denomination, probe HTTP,
query crt.sh Certificate Transparency log for subdomains.

Usage: osint_companies.py [--limit N]
Env: DSN
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys, time
import unicodedata
import urllib.request, urllib.parse, socket
import psycopg
from psycopg.types.json import Jsonb
from datetime import datetime


def _slug_domain(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    # Strip corporate suffixes
    for suf in (" SAS", " SA", " SARL", " SCA", " SNC", " EURL", " SCS", " SCI",
                " GROUP", " GROUPE", " HOLDING", " INVEST", " FRANCE"):
        if s.upper().endswith(suf):
            s = s[: -len(suf)]
    s = re.sub(r"[^a-zA-Z0-9]+", "", s).lower()
    return s[:30]


def guess_domains(denomination: str, nom_commercial: str | None = None) -> list[str]:
    candidates: set[str] = set()
    for src in filter(None, (denomination, nom_commercial)):
        slug = _slug_domain(src)
        if not slug or len(slug) < 3:
            continue
        for tld in (".fr", ".com"):
            candidates.add(slug + tld)
        # With hyphen if multi-word
        slug_hy = re.sub(r"[^a-zA-Z0-9]+", "-", unicodedata.normalize("NFKD", src)
                          .encode("ASCII", "ignore").decode()).strip("-").lower()
        if slug_hy and slug_hy != slug:
            for tld in (".fr", ".com"):
                candidates.add(slug_hy[:40] + tld)
    return list(candidates)[:6]


def probe_domain(domain: str, timeout: int = 5) -> bool:
    try:
        socket.gethostbyname(domain)
        # Quick HTTP HEAD
        try:
            req = urllib.request.Request(f"https://{domain}", method="HEAD",
                                          headers={"User-Agent": "DEMOEMA-OSINT/0.1"})
            urllib.request.urlopen(req, timeout=timeout)
            return True
        except Exception:
            # DNS resolves but HTTP failed — still a valid domain possibly
            return True
    except (socket.gaierror, socket.timeout):
        return False


def crt_sh_subdomains(domain: str, timeout: int = 20) -> list[str]:
    """Query crt.sh for certificate transparency log entries."""
    try:
        url = f"https://crt.sh/?q=%25.{urllib.parse.quote(domain)}&output=json"
        req = urllib.request.Request(url, headers={"User-Agent": "DEMOEMA-OSINT/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", errors="ignore"))
        names = set()
        for row in data[:500]:
            name_value = row.get("name_value") or ""
            for n in name_value.split("\n"):
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100)
    args = ap.parse_args()

    dsn = os.environ["DSN"]
    t0 = time.time()
    n_scanned = n_with_domain = total_subdomains = 0

    with psycopg.connect(dsn, autocommit=False) as conn, conn.cursor() as cur:
        cur.execute(PICK_SQL, (args.limit,))
        rows = cur.fetchall()
        print(f"picked {len(rows)} companies", file=sys.stderr)

        for (siren, denom, nomcom) in rows:
            candidates = guess_domains(denom, nomcom)
            validated = [d for d in candidates if probe_domain(d)]
            subdomains: list[str] = []
            for d in validated[:3]:   # crt.sh only on top-3 validated
                subdomains.extend(crt_sh_subdomains(d))
            subdomains = sorted(set(subdomains))[:500]

            payload = {
                "candidates_tried": candidates,
                "denomination": denom,
                "scanned_at": datetime.utcnow().isoformat(),
            }

            with conn.cursor() as ucur:
                ucur.execute(UPSERT_SQL, (
                    siren,
                    validated or None,
                    subdomains or None,
                    ["domain_guess", "crt_sh"],
                    Jsonb(payload),
                ))
            conn.commit()

            n_scanned += 1
            if validated:
                n_with_domain += 1
            total_subdomains += len(subdomains)

            if n_scanned % 20 == 0:
                print(f"[{n_scanned}/{len(rows)}] {denom[:40]} -> {len(validated)} domains, "
                      f"{len(subdomains)} subdomains",
                      file=sys.stderr, flush=True)

    print(json.dumps({
        "scanned": n_scanned,
        "with_domain": n_with_domain,
        "total_subdomains": total_subdomains,
        "duration_s": round(time.time() - t0, 1),
    }))


if __name__ == "__main__":
    main()
