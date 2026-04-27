#!/usr/bin/env bash
# DEMOEMA — comparaison table-à-table entre 2 VPS (validation post-migration).
#
# Pour chaque schema (bronze, silver, audit), liste les tables/MV de chaque
# VPS, compare les row counts. Signale :
#   ✓ matche                  : count source == count target
#   ⚠️  écart                  : count diff non-nul (acceptable si delta
#                              ingest a tourné depuis le snapshot)
#   ❌ manquante sur target    : présente source, absente target
#   ❌ orpheline sur target    : absente source, présente target
#
# Usage :
#   ./compare-vps.sh \
#       --source root@OLD_HOST \
#       --target root@NEW_HOST \
#       [--ssh-key ~/.ssh/demoema_ionos_ed25519] \
#       [--mode quick|exact] \
#       [--schema bronze,silver,audit]
#
# --mode quick   (default) : pg_class.reltuples (estimation, < 1ms/table)
# --mode exact   : count(*) — lent mais exact (~5min sur big tables)
# --schema       : comma-separated, default = bronze,silver,audit
#
# Le script ne modifie RIEN — read-only sur les 2 VPS.

set -euo pipefail

SOURCE=""
TARGET=""
SSH_KEY="${SSH_KEY:-$HOME/.ssh/demoema_ionos_ed25519}"
MODE="quick"
SCHEMAS="bronze,silver,audit"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --source) SOURCE="$2"; shift 2 ;;
        --target) TARGET="$2"; shift 2 ;;
        --ssh-key) SSH_KEY="$2"; shift 2 ;;
        --mode) MODE="$2"; shift 2 ;;
        --schema) SCHEMAS="$2"; shift 2 ;;
        -h|--help) grep '^#' "$0" | head -25; exit 0 ;;
        *) echo "Unknown arg: $1" >&2; exit 1 ;;
    esac
done

[ -n "$SOURCE" ] || { echo "ERROR: --source required" >&2; exit 1; }
[ -n "$TARGET" ] || { echo "ERROR: --target required" >&2; exit 1; }

SSH_OPTS="-i $SSH_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"

# Build SQL selon le mode. Renvoie (schema, table, count) triés par schema.
if [ "$MODE" = "exact" ]; then
    # count(*) exact via xpath query_to_xml (truc psql connu pour count
    # dynamique cross-schema dans une seule query).
    SQL=$(cat <<'EOSQL'
SELECT n.nspname AS schema_name,
       c.relname AS object_name,
       (xpath('/row/c/text()',
              query_to_xml(format('SELECT count(*) AS c FROM %I.%I', n.nspname, c.relname),
                           false, true, '')))[1]::text::bigint AS row_count
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname IN (__SCHEMA_LIST__)
  AND c.relkind IN ('r', 'm')
ORDER BY n.nspname, c.relname;
EOSQL
)
else
    # reltuples (estimation, à jour après ANALYZE)
    SQL=$(cat <<'EOSQL'
SELECT n.nspname AS schema_name,
       c.relname AS object_name,
       c.reltuples::bigint AS row_count
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname IN (__SCHEMA_LIST__)
  AND c.relkind IN ('r', 'm')
ORDER BY n.nspname, c.relname;
EOSQL
)
fi

# Convert "bronze,silver,audit" → "'bronze','silver','audit'"
SCHEMA_LIST=$(printf "%s" "$SCHEMAS" | sed "s/,/','/g; s/^/'/; s/$/'/")
SQL=$(printf "%s" "$SQL" | sed "s/__SCHEMA_LIST__/${SCHEMA_LIST}/")

# Récupère les counts des 2 VPS en parallèle
TMP_SRC=$(mktemp)
TMP_TGT=$(mktemp)
trap "rm -f $TMP_SRC $TMP_TGT" EXIT

echo "[compare] mode=$MODE schemas=$SCHEMAS" >&2
echo "[compare] fetching counts depuis $SOURCE..." >&2
ssh $SSH_OPTS "$SOURCE" "docker exec demomea-datalake-db psql -U postgres -d datalake -tAF '|' -c \"$SQL\"" > "$TMP_SRC" 2>/dev/null &
SRC_PID=$!

echo "[compare] fetching counts depuis $TARGET..." >&2
ssh $SSH_OPTS "$TARGET" "docker exec demomea-datalake-db psql -U postgres -d datalake -tAF '|' -c \"$SQL\"" > "$TMP_TGT" 2>/dev/null &
TGT_PID=$!

wait $SRC_PID $TGT_PID

# Compare via Python — détection cross-platform robuste.
# Sur Windows, `python3` peut être un shim du Microsoft Store qui ouvre
# l'app au lieu d'exécuter — donc on TESTE chaque binaire avec --version.
PYTHON_BIN=""
for bin in python3 python py; do
    if command -v "$bin" >/dev/null && "$bin" --version >/dev/null 2>&1; then
        PYTHON_BIN="$bin"
        break
    fi
done
[ -n "$PYTHON_BIN" ] || { echo "ERROR: python introuvable (besoin python3, python ou py)" >&2; exit 1; }
"$PYTHON_BIN" - "$TMP_SRC" "$TMP_TGT" <<'PYEOF'
import sys

src_path, tgt_path = sys.argv[1], sys.argv[2]

def parse(path):
    out = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('|')
            if len(parts) != 3:
                continue
            schema, name, count_str = parts
            try:
                count = int(count_str)
            except ValueError:
                count = 0
            out[(schema, name)] = count
    return out

src = parse(src_path)
tgt = parse(tgt_path)

all_keys = sorted(set(src) | set(tgt))

n_match = n_diff = n_missing = n_orphan = 0
diffs = []
missing = []
orphans = []

for key in all_keys:
    schema, name = key
    s = src.get(key)
    t = tgt.get(key)
    if s is None:
        n_orphan += 1
        orphans.append((schema, name, t))
    elif t is None:
        n_missing += 1
        missing.append((schema, name, s))
    elif s == t:
        n_match += 1
    else:
        n_diff += 1
        delta = t - s
        pct = (100.0 * delta / s) if s != 0 else 0.0
        diffs.append((schema, name, s, t, delta, pct))

# Output structuré
print(f"\n{'='*80}")
print(f"COMPARAISON {sys.argv[1]} (source) vs {sys.argv[2]} (target)")
print(f"{'='*80}")
print(f"Tables/MV match exact     : {n_match}")
print(f"Tables/MV avec écart      : {n_diff}")
print(f"Manquantes sur target     : {n_missing}")
print(f"Orphelines sur target     : {n_orphan}")
print(f"Total comparées           : {len(all_keys)}")

if missing:
    print(f"\n❌ MANQUANTES sur target ({n_missing}) :")
    for schema, name, s in missing:
        print(f"   {schema}.{name:50s} source={s:>15,}")

if orphans:
    print(f"\n❌ ORPHELINES sur target ({n_orphan}) :")
    for schema, name, t in orphans:
        print(f"   {schema}.{name:50s} target={t:>15,}")

if diffs:
    print(f"\n⚠️  ÉCARTS ({n_diff}) :")
    print(f"   {'schema.table':<60s} {'source':>15s} {'target':>15s} {'delta':>15s} {'pct':>8s}")
    for schema, name, s, t, delta, pct in sorted(diffs, key=lambda x: -abs(x[5])):
        print(f"   {schema+'.'+name:<60s} {s:>15,} {t:>15,} {delta:>+15,} {pct:>+7.2f}%")

print(f"\n{'='*80}")
if n_missing == 0 and n_orphan == 0 and n_diff == 0:
    print("✅ MIGRATION VALIDÉE — toutes les tables matchent à l'identique")
elif n_missing == 0 and n_orphan == 0:
    print(f"⚠️  MIGRATION OK avec {n_diff} écarts (acceptable si delta ingest a tourné)")
else:
    print(f"❌ MIGRATION INCOMPLÈTE — {n_missing} manquantes, {n_orphan} orphelines")
    sys.exit(2)
print(f"{'='*80}\n")
PYEOF
