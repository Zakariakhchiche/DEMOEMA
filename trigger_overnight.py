"""
EdRCF 6.0 — trigger_overnight.py
Lance le pipeline overnight complet sur Render.

Usage :
  python trigger_overnight.py
  python trigger_overnight.py --url https://mon-service.onrender.com
  python trigger_overnight.py --url https://... --secret MON_SECRET --rne 1000
  python trigger_overnight.py --skip-bronze   # si SIRENE déjà chargé (recommandé 2nd run+)
"""

import argparse
import json
import sys
import time
import urllib.request

# ── Config par défaut ────────────────────────────────────────────────────────
DEFAULT_URL    = "https://demoema.onrender.com"
SINCE_BODACC   = "2023-01-01"
RNE_N          = 500       # nombre d'entreprises Silver enrichies via INPI RNE
POLL_INTERVAL  = 60        # secondes entre chaque check de statut
MAX_WAIT_MIN   = 90        # timeout total en minutes


def call(url: str, secret: str = "") -> dict:
    full = url + (f"?secret={secret}" if secret else "")
    req = urllib.request.Request(full, headers={"User-Agent": "EdRCF/trigger"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url",         default=DEFAULT_URL)
    parser.add_argument("--secret",      default="")
    parser.add_argument("--rne",         type=int, default=RNE_N)
    parser.add_argument("--skip-bronze", action="store_true",
                        help="Saute le reload SIRENE (recommandé si déjà chargé)")
    args = parser.parse_args()

    base   = args.url.rstrip("/")
    secret = args.secret
    qs     = f"?since_bodacc={SINCE_BODACC}&rne_n={args.rne}"
    if args.skip_bronze:
        qs += "&skip_bronze=true"
    qs    += f"&secret={secret}" if secret else ""

    print(f"\n[TRIGGER] Backend : {base}")
    print(f"[TRIGGER] BODACC depuis : {SINCE_BODACC}")
    print(f"[TRIGGER] RNE top-N : {args.rne}")

    # 1. Health check
    print("\n[1/3] Health check…")
    try:
        h = call(f"{base}/api/health")
        print(f"      Status : {h.get('status','?')}")
    except Exception as e:
        print(f"      ERREUR health check : {e}")
        print("      Verifiez que le service Render est bien deploye.")
        sys.exit(1)

    # 2. Lancer run-all
    print("\n[2/3] Lancement pipeline run-all…")
    try:
        r = call(f"{base}/api/admin/run-all{qs}")
        print(f"      Reponse : {r.get('status','?')} — {r.get('message','')}")
    except Exception as e:
        print(f"      ERREUR run-all : {e}")
        sys.exit(1)

    # 3. Polling statut
    print(f"\n[3/3] Suivi progression (poll toutes les {POLL_INTERVAL}s)…")
    start = time.time()
    last_step = ""

    while True:
        elapsed = (time.time() - start) / 60
        if elapsed > MAX_WAIT_MIN:
            print(f"\n[TIMEOUT] {MAX_WAIT_MIN} min ecoulees. Verifiez manuellement :")
            print(f"  GET {base}/api/admin/bronze-stats")
            break

        time.sleep(POLL_INTERVAL)
        try:
            stats = call(f"{base}/api/admin/bronze-stats" + (f"?secret={secret}" if secret else ""))
            p     = stats.get("pipeline", {})
            step  = p.get("step", "?")
            running = p.get("running", False)
            err   = p.get("error")

            if step != last_step:
                print(f"  [{elapsed:4.0f} min] step={step} | "
                      f"bronze={stats.get('bronze_total',0):,} | "
                      f"silver={stats.get('silver_eligible',0):,} | "
                      f"bodacc={stats.get('bodacc_total',0):,} | "
                      f"bodacc_flagged={stats.get('bodacc_flagged_silver',0):,}")
                last_step = step

            if err:
                print(f"\n[ERREUR] {err}")
                break
            if not running and step == "done":
                print(f"\n[OK] Pipeline termine en {elapsed:.0f} min !")
                print(f"  Bronze  : {stats.get('bronze_total',0):,} entites")
                print(f"  Silver  : {stats.get('silver_eligible',0):,} PME/ETI eligibles")
                print(f"  BODACC  : {stats.get('bodacc_total',0):,} annonces")
                print(f"  Flagges : {stats.get('bodacc_flagged_silver',0):,} entreprises avec signal BODACC")
                print(f"  Score moyen : {stats.get('silver_avg_score',0)}")
                break
        except Exception as e:
            print(f"  [{elapsed:4.0f} min] Erreur poll : {e}")

    print("\n[TRIGGER] Termine. Bonne nuit !")


if __name__ == "__main__":
    main()
