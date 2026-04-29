#!/usr/bin/env python3
"""OSINT Orchestrator — enrich dirigeants from inpi_formalites_personnes via
Maigret (username -> social profiles) + Holehe (email -> services).

Usage:
    osint_orchestrator.py [--limit N] [--top-sites N]
    Env: DSN=postgres://...

Runs inside agents-platform container; delegates to maigret/holehe
containers via docker run (see DOCKER_NETWORK).
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys, time
from datetime import datetime
import psycopg
from psycopg.types.json import Jsonb


# ─── Helpers ──────────────────────────────────────────────────────────────

def _slug(s: str) -> str:
    """Normalize a name: lowercase, ASCII, no accents, no spaces."""
    if not s:
        return ""
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    s = re.sub(r"[^a-zA-Z0-9]", "", s).lower()
    return s


def person_uid(nom: str, prenoms: list, date_naissance: str, siren: str) -> str:
    parts = [_slug(nom), _slug((prenoms or [""])[0]), date_naissance or "", siren or ""]
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:40]


def username_candidates(nom: str, prenoms: list) -> list[str]:
    """Generate plausible usernames — ONLY combined (prenom+nom). Single-part
    usernames (just 'alexandre' or just 'blanc') produce massive false positives
    because many unrelated people share common first/last names."""
    n = _slug(nom)
    if not n or len(n) < 3:
        return []
    candidates: set[str] = set()
    for p in (prenoms or []):
        ps = _slug(p)
        if not ps or len(ps) < 2:
            continue
        # Combined forms only — much more discriminating
        candidates.add(f"{ps}{n}")
        candidates.add(f"{ps}.{n}")
        candidates.add(f"{ps}_{n}")
        candidates.add(f"{ps[0]}{n}")            # aauthier
        candidates.add(f"{n}{ps}")
        candidates.add(f"{n}.{ps}")
    # Only combined username candidates pass: ensure at least 6 chars
    return [c for c in candidates if 6 <= len(c) <= 40]


# Sites returning HTTP 200 on ANY username — untrustworthy for OSINT
UNRELIABLE_SITES = {
    "tiktok online viewer", "tiktok", "bit.ly", "wordpressorg",
    "tikbuddy.com", "vimeo", "amazon", "wordpress", "wikipedia",
    "telegram", "tumblr", "spotify",
}


def email_candidates(nom: str, prenoms: list, domains: list[str]) -> list[str]:
    """prenom.nom@domain, etc."""
    if not domains:
        return []
    n = _slug(nom)
    locals_ = set()
    for p in (prenoms or []):
        ps = _slug(p)
        if not ps:
            continue
        locals_.add(f"{ps}.{n}")
        locals_.add(f"{ps}{n}")
        locals_.add(f"{ps[0]}.{n}")
        locals_.add(f"{ps[0]}{n}")
    locals_.add(n)
    return [f"{loc}@{d}" for loc in locals_ for d in domains][:20]


# ─── Tools wrappers ───────────────────────────────────────────────────────

DOCKER_NETWORK = os.environ.get("OSINT_DOCKER_NET", "demomea-agents_default")


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_HIT_RE = re.compile(r"^\s*\[\+\]\s+([^:]+?):\s+(https?://\S+)")


def run_maigret(username: str, top_sites: int = 50, timeout: int = 120) -> list[dict]:
    """Run maigret CLI on username; parse stdout [+] hits lines."""
    cmd = [
        "docker", "run", "--rm", "soxoj/maigret:latest",
        username, "--top-sites", str(top_sites),
        "--no-progressbar", "--retries", "1", "--timeout", "8",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return []
    accounts = []
    for line in proc.stdout.splitlines():
        clean = _ANSI_RE.sub("", line)
        m = _HIT_RE.match(clean)
        if m:
            accounts.append({
                "site": m.group(1).strip(),
                "url": m.group(2).strip(),
                "username": username,
            })
    return accounts


def run_holehe(email: str, timeout: int = 45) -> dict:
    """Run holehe CLI on email; parse plain-text output."""
    cmd = ["docker", "run", "--rm", "--network", DOCKER_NETWORK,
           "megadose/holehe:latest", email, "--only-used", "--no-color"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"email": email, "services": [], "timeout": True}
    services = []
    for line in proc.stdout.splitlines():
        # Holehe prints "[+] service.com" for positive hits
        m = re.match(r"^\s*\[\+\]\s+(\S+)", line)
        if m:
            services.append(m.group(1).strip())
    return {"email": email, "services": services}


# ─── Main pipeline ────────────────────────────────────────────────────────

PICK_SQL = """
-- M&A-relevant targeting (29/04/2026 — switched from montant_capital filter to
-- pro_ma_score). Le filtre montant_capital >= 500k limitait à ~2K dirigeants ;
-- pro_ma_score >= 50 cible ~150K Tier 1+2 (multi-axes : holding/co-mandataires/
-- patrimoine SCI/secteur). Voir silver.dirigeants_360 + gold.dirigeants_master.
--
-- Stratégie multi-axes (UNION) :
--   1. pro_ma_score >= 50 dans gold.dirigeants_master (priorité)
--   2. is_pro_ma (n_mandats_actifs >= 10) — multi-mandats
--   3. has_holding_patrimoniale = true
--   4. n_co_mandataires >= 5 — réseaux denses
--   5. SAS/SA capital >= 100k (au lieu de 500k) — fallback historique étendu
WITH targets AS (
  SELECT p.representant_id, p.siren, p.individu_nom, p.individu_prenoms, p.individu_date_naissance
  FROM bronze.inpi_formalites_personnes p
  JOIN bronze.inpi_formalites_entreprises e ON e.siren = p.siren
  -- LEFT JOIN gold/silver (peut ne pas exister sur fresh boot)
  LEFT JOIN silver.inpi_dirigeants d
    ON d.nom = p.individu_nom
   AND d.prenom = (p.individu_prenoms->>0)
   AND d.date_naissance = p.individu_date_naissance::date
  -- Optional join gold.dirigeants_master pour pro_ma_score (peut ne pas exister)
  LEFT JOIN gold.dirigeants_master gd ON gd.person_uid = d.person_uid
  WHERE p.type_de_personne = 'INDIVIDU'
    AND p.actif = true
    AND p.individu_nom IS NOT NULL
    AND length(p.individu_nom) > 2
    AND p.siren IS NOT NULL
    AND (
        -- Axis 1 : top scoring M&A (gold dispo)
        gd.pro_ma_score >= 50
        -- Axis 2 : multi-mandats
        OR d.n_mandats_actifs >= 10
        -- Axis 3 : holding patrimoniale
        OR coalesce((SELECT count(*) FROM silver.dirigeant_sci_patrimoine sci
                     WHERE sci.nom = d.nom AND sci.prenom = d.prenom
                       AND sci.date_naissance = d.date_naissance), 0) >= 2
        -- Axis 4 : SAS/SA capital >= 100k (fallback étendu vs 500k)
        OR (e.forme_juridique IN ('5710','5720','5730','5485','5499','5505','5510','5515','5520','5530','5540','5599',
                                  '5385','5308','5306','5202','5203')
            AND COALESCE(e.montant_capital, 0) >= 100000)
    )
    AND p.representant_id NOT IN (
        SELECT representant_id FROM bronze.osint_persons
        WHERE representant_id IS NOT NULL AND last_scanned_at > now() - interval '90 days'
    )
)
SELECT t.*
FROM targets t
JOIN bronze.inpi_formalites_entreprises e ON e.siren = t.siren
LEFT JOIN silver.inpi_dirigeants d
  ON d.nom = t.individu_nom AND d.prenom = (t.individu_prenoms->>0)
LEFT JOIN gold.dirigeants_master gd ON gd.person_uid = d.person_uid
ORDER BY
  -- Priorité 1 : pro_ma_score si dispo, sinon montant_capital, sinon nb mandats
  coalesce(gd.pro_ma_score, 0) DESC,
  coalesce(e.montant_capital, 0) DESC NULLS LAST,
  coalesce(d.n_mandats_actifs, 0) DESC,
  t.siren
LIMIT %s
"""

UPSERT_SQL = """
INSERT INTO bronze.osint_persons
  (person_uid, siren_main, representant_id, nom, prenoms, date_naissance,
   linkedin_urls, github_usernames, twitter_handles, instagram_handles,
   medium_profiles, crunchbase_url, facebook_urls, youtube_channels,
   other_sites, emails_tested, emails_valid, email_services,
   sources_scanned, last_scanned_at, payload)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), %s)
ON CONFLICT (person_uid) DO UPDATE SET
  linkedin_urls = EXCLUDED.linkedin_urls,
  github_usernames = EXCLUDED.github_usernames,
  twitter_handles = EXCLUDED.twitter_handles,
  instagram_handles = EXCLUDED.instagram_handles,
  medium_profiles = EXCLUDED.medium_profiles,
  crunchbase_url = EXCLUDED.crunchbase_url,
  facebook_urls = EXCLUDED.facebook_urls,
  youtube_channels = EXCLUDED.youtube_channels,
  other_sites = EXCLUDED.other_sites,
  emails_tested = EXCLUDED.emails_tested,
  emails_valid = EXCLUDED.emails_valid,
  email_services = EXCLUDED.email_services,
  sources_scanned = EXCLUDED.sources_scanned,
  last_scanned_at = now(),
  payload = EXCLUDED.payload
"""


def categorize_accounts(accounts: list[dict]) -> dict:
    """Split Maigret findings into typed columns. Drops unreliable site hits."""
    out = {
        "linkedin": [], "github": [], "twitter": [], "instagram": [],
        "medium": [], "facebook": [], "youtube": [],
        "crunchbase": None, "other": {},
    }
    seen_urls = set()
    for a in accounts:
        site = (a.get("site") or "").lower()
        url = a.get("url") or ""
        if url in seen_urls:
            continue
        seen_urls.add(url)
        # Unreliable sites may have suffix variants like "[tiktok]" — use substring match
        if any(bad in site for bad in UNRELIABLE_SITES):
            continue
        if "linkedin" in site:
            out["linkedin"].append(url)
        elif "github" in site:
            out["github"].append(a.get("username"))
        elif "twitter" in site or site == "x":
            out["twitter"].append(a.get("username"))
        elif "instagram" in site:
            out["instagram"].append(a.get("username"))
        elif "medium" in site:
            out["medium"].append(url)
        elif "facebook" in site:
            out["facebook"].append(url)
        elif "youtube" in site:
            out["youtube"].append(url)
        elif "crunchbase" in site:
            out["crunchbase"] = url
        else:
            out["other"].setdefault(site, []).append(url)
    # Dedup arrays
    for k in ("linkedin", "github", "twitter", "instagram", "medium", "facebook", "youtube"):
        if isinstance(out[k], list):
            out[k] = list(dict.fromkeys(out[k]))
    return out


def enrich_one(cur, row: tuple, top_sites: int, with_holehe: bool = False):
    representant_id, siren, nom, prenoms, date_naissance = row
    uid = person_uid(nom, prenoms, date_naissance, siren)
    usernames = username_candidates(nom, prenoms)[:3]  # Top 3 to limit API calls
    all_accounts = []
    for u in usernames:
        accounts = run_maigret(u, top_sites=top_sites)
        all_accounts.extend(accounts)

    cat = categorize_accounts(all_accounts)

    # Holehe: skipped by default (slow + requires domain guesses)
    emails_tested = []
    emails_valid = []
    email_services: dict = {}

    payload = {
        "raw_accounts": all_accounts,
        "usernames_tried": usernames,
        "top_sites": top_sites,
        "scanned_at": datetime.utcnow().isoformat(),
    }

    cur.execute(UPSERT_SQL, (
        uid, siren, representant_id, nom, prenoms, date_naissance,
        cat["linkedin"] or None,
        cat["github"] or None,
        cat["twitter"] or None,
        cat["instagram"] or None,
        cat["medium"] or None,
        cat["crunchbase"],
        cat["facebook"] or None,
        cat["youtube"] or None,
        Jsonb(cat["other"]) if cat["other"] else None,
        emails_tested or None,
        emails_valid or None,
        Jsonb(email_services) if email_services else None,
        ["maigret"] + (["holehe"] if with_holehe else []),
        Jsonb(payload),
    ))
    return {"uid": uid, "nom": nom, "accounts_found": len(all_accounts)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--top-sites", type=int, default=50)
    ap.add_argument("--with-holehe", action="store_true")
    args = ap.parse_args()

    dsn = os.environ.get("DSN")
    if not dsn:
        print("DSN env var required", file=sys.stderr)
        sys.exit(2)

    t0 = time.time()
    n_done = 0
    n_with_hits = 0
    total_accounts = 0

    with psycopg.connect(dsn, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(PICK_SQL, (args.limit,))
            rows = cur.fetchall()
            print(f"picked {len(rows)} persons to enrich", file=sys.stderr)

        for row in rows:
            try:
                with conn.cursor() as cur:
                    res = enrich_one(cur, row, args.top_sites, args.with_holehe)
                conn.commit()
                n_done += 1
                total_accounts += res["accounts_found"]
                if res["accounts_found"] > 0:
                    n_with_hits += 1
                if n_done % 10 == 0:
                    print(f"[{n_done}/{len(rows)}] {res['nom']} -> {res['accounts_found']} accounts",
                          file=sys.stderr, flush=True)
            except Exception as e:
                conn.rollback()
                print(f"err: {type(e).__name__}: {e}", file=sys.stderr)

    print(json.dumps({
        "enriched": n_done,
        "with_hits": n_with_hits,
        "total_accounts_found": total_accounts,
        "duration_s": round(time.time() - t0, 1),
    }))


if __name__ == "__main__":
    main()
