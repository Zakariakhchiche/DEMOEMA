#!/bin/bash
# Backfill DILA complet : codegen 7 nouveaux fetchers + run 11 dila_* en parallèle.
#
# Usage (depuis local) :
#   scp -i ~/.ssh/demoema_ionos_ed25519 backfill_dila.sh root@TARGET:/tmp/
#   ssh root@TARGET 'chmod +x /tmp/backfill_dila.sh && /tmp/backfill_dila.sh'
#
# Aucun secret hardcoded — utilise uniquement settings.database_url depuis .env du container.

set -e

cat > /tmp/backfill_dila_inner.py <<'PYEOF'
# (le inner.py est écrit sur le host, copié dans le container ensuite via docker cp)
PYEOF
cat > /tmp/backfill_dila_inner.py <<'PYEOF'
import asyncio
import time
from datetime import datetime, timezone

async def main():
    # Phase 1 : codegen tous les fetchers manquants (incluant les 7 DILA nouveaux)
    print(f"[{datetime.now(timezone.utc).isoformat()}] PHASE 1 codegen", flush=True)
    from ingestion.bronze_bootstrap import run_bronze_bootstrap_tick, list_missing_fetchers
    missing_before = list_missing_fetchers()
    print(f"  {len(missing_before)} missing fetchers : {missing_before}", flush=True)
    if missing_before:
        r = await run_bronze_bootstrap_tick()
        print(f"  result: ok={r.get('ok',0)} fail={r.get('fail',0)}", flush=True)

    # Phase 2 : rediscover SOURCES (nouveaux .py loadés)
    from ingestion.engine import _discover_agent_generated_sources, SOURCES, run_source
    _discover_agent_generated_sources()

    # Phase 3 : run all dila_* fetchers en parallèle (Semaphore=4)
    dila_sources = sorted([s for s in SOURCES if s.startswith('dila_')])
    print(f"\n[{datetime.now(timezone.utc).isoformat()}] PHASE 3 fetch {len(dila_sources)} DILA sources", flush=True)
    print(f"  sources: {dila_sources}", flush=True)

    sem = asyncio.Semaphore(4)  # 4 concurrent (chacune ~50-200 MB d'archives)
    n_done = 0
    started = time.time()

    async def one(sid):
        nonlocal n_done
        async with sem:
            t0 = time.time()
            try:
                r = await run_source(sid)
                rows = r.get('rows', 0) if isinstance(r, dict) else 0
                err = r.get('error') if isinstance(r, dict) else None
                status = 'OK' if not err else 'FAIL'
            except Exception as e:
                rows = 0
                err = f'{type(e).__name__}: {e}'
                status = 'EXC'
            dur = int(time.time() - t0)
            n_done += 1
            elapsed = int(time.time() - started)
            err_str = f" err={err[:80]}" if err else ""
            print(f"  [{n_done}/{len(dila_sources)} {elapsed:>5}s] {status:<4} {sid:<20} rows={rows} dur={dur}s{err_str}", flush=True)
            return sid, status, rows, err

    results = await asyncio.gather(*[one(s) for s in dila_sources])
    total = int(time.time() - started)
    ok = sum(1 for _, st, *_ in results if st == 'OK')
    total_rows = sum(r if isinstance(r, int) else 0 for _, _, r, _ in results)
    print(f"\n[{datetime.now(timezone.utc).isoformat()}] DILA BACKFILL DONE", flush=True)
    print(f"  {ok}/{len(dila_sources)} ok, total_rows={total_rows}, duration={total}s", flush=True)

asyncio.run(main())
PYEOF

# Copie le script inner.py DANS le container (sinon /tmp/ pointe vers l'host)
docker cp /tmp/backfill_dila_inner.py demomea-agents-platform:/tmp/backfill_dila_inner.py

# Run dans le container en background
docker exec -d demomea-agents-platform sh -c 'PYTHONPATH=/app python -u /tmp/backfill_dila_inner.py > /tmp/backfill_dila.log 2>&1'
echo "Lancé en background dans container. Log: /tmp/backfill_dila.log"
sleep 5
echo ""
echo "=== first 10 lines ==="
docker exec demomea-agents-platform tail -10 /tmp/backfill_dila.log
