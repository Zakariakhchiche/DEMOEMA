#!/usr/bin/env bash
# Driver : attend extraction, lance 8-way parallel ingest, recrée les indexes.
# Logs dans /root/inpi_dumps/ingest.log
set -u  # ne pas utiliser -e : xargs peut avoir des fichiers individuels qui échouent

LOG=/root/inpi_dumps/ingest.log
DIR=/root/inpi_dumps/comptes

exec > >(tee -a "$LOG") 2>&1

echo "[$(date -Iseconds)] === waiting for unzip to finish ==="
while [ ! -f /root/inpi_dumps/.extract_done ]; do sleep 20; done
N_FILES=$(ls "$DIR"/stock_*.json 2>/dev/null | wc -l)
echo "[$(date -Iseconds)] extract done — $N_FILES files ready"

echo "[$(date -Iseconds)] === launching 8-way parallel ingest ==="
T0=$(date +%s)

# Run ingestion via agents-platform container. Files mounted at /inpi_dumps/comptes/.
# Source DSN from settings module inside container.
docker exec demomea-agents-platform bash -c '
  source <(python3 -c "from config import settings; print(f\"export DSN={settings.database_url}\")")
  ls /inpi_dumps/comptes/stock_*.json | xargs -P 8 -I{} python3 /tmp/ingest_comptes_fast.py {}
' | tee -a "$LOG" | awk -v total="$N_FILES" '
  BEGIN { done = 0 }
  /"file":/ {
    done++
    if (done % 20 == 0 || done == total) {
      printf "[PROGRESS] %d / %d files done\n", done, total > "/dev/stderr"
    }
  }
  { print }
'

T1=$(date +%s)
DUR=$((T1-T0))
echo "[$(date -Iseconds)] === ingest done in ${DUR}s ==="

echo "[$(date -Iseconds)] === recreating indexes ==="
docker exec demomea-datalake-db /usr/local/bin/psql -U postgres -d datalake -c "
  CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_liasses_siren_code
      ON bronze.inpi_comptes_liasses(siren, code);
  CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_liasses_code
      ON bronze.inpi_comptes_liasses(code);
" 2>&1 | tee -a "$LOG"

echo "[$(date -Iseconds)] === ALL DONE ==="
docker exec demomea-datalake-db /usr/local/bin/psql -U postgres -d datalake -c "
  SELECT 'depots' AS table, count(*) FROM bronze.inpi_comptes_depots
  UNION ALL SELECT 'identites', count(*) FROM bronze.inpi_comptes_identite
  UNION ALL SELECT 'liasses', count(*) FROM bronze.inpi_comptes_liasses;
" 2>&1 | tee -a "$LOG"
