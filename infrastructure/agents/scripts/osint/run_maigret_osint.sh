#!/usr/bin/env bash
# ============================================================================
# Maigret + Holehe OSINT enrichment runner (DEMOEMA).
#
# Tourne SUR LE VPS (host). Délègue au container agents-platform via
# `docker exec` qui :
#   1. Pick les dirigeants Tier 1+2 dans bronze.inpi_formalites_personnes
#      via PICK_SQL (skip ceux scannés < 90j)
#   2. Génère 6 username candidates par dirigeant (prenom+nom combos)
#   3. Lance `docker run --rm soxoj/maigret:latest` sur top 50 sites
#   4. Catégorise les hits → bronze.osint_persons (UPSERT)
#   5. (Optionnel) Lance Holehe sur les emails dérivés
#
# Pré-requis :
#   - Tourne sur 82.165.57.191 (VPS IONOS) avec ~/DEMOEMA cloné
#   - Containers demomea-agents-platform + demomea-datalake-db UP
#   - Le container agents-platform a le socket Docker monté (vérifié au boot)
#
# Modes :
#   $0 test        # --limit 5 (validation setup, ~3 min)
#   $0 batch       # --limit 500 (run nocturne, ~5h)
#   $0 aggressive  # --limit 2000 (rattrapage, ~20h)
#   $0 holehe      # --limit 100 --with-holehe (emails)
#   $0 status      # affiche stats bronze.osint_persons
#
# Usage par cron : voir install_osint_cron.sh
# ============================================================================
set -euo pipefail

REPO_DIR="${REPO_DIR:-/root/DEMOEMA}"
LOG_DIR="/var/log/osint"
LOG_FILE="${LOG_DIR}/maigret_$(date +%Y%m%d_%H%M%S).log"
AGENTS_CONTAINER="demomea-agents-platform"
DATALAKE_CONTAINER="demomea-datalake-db"
ORCHESTRATOR_REL_PATH="infrastructure/agents/scripts/osint/osint_orchestrator.py"

# ─── Helpers ─────────────────────────────────────────────────────────────
red()    { printf "\033[31m%s\033[0m\n" "$*" >&2; }
green()  { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }
blue()   { printf "\033[34m%s\033[0m\n" "$*"; }

die() { red "ERROR: $*"; exit 1; }

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

# ─── Pre-flight ──────────────────────────────────────────────────────────
preflight() {
    blue "[1/5] Preflight checks..."
    require_cmd docker
    require_cmd grep
    require_cmd awk

    [ -d "$REPO_DIR" ] || die "REPO_DIR not found: $REPO_DIR"
    [ -f "${REPO_DIR}/.env" ] || die "${REPO_DIR}/.env not found"
    [ -f "${REPO_DIR}/${ORCHESTRATOR_REL_PATH}" ] || \
        die "orchestrator script not found at ${ORCHESTRATOR_REL_PATH}"

    # Check containers up
    docker ps --format '{{.Names}}' | grep -q "^${AGENTS_CONTAINER}$" || \
        die "container ${AGENTS_CONTAINER} not running. Run: docker compose up -d ${AGENTS_CONTAINER}"
    docker ps --format '{{.Names}}' | grep -q "^${DATALAKE_CONTAINER}$" || \
        die "container ${DATALAKE_CONTAINER} not running."

    # Docker socket inside agents-platform (needed to docker run maigret)
    docker exec "${AGENTS_CONTAINER}" sh -c 'test -S /var/run/docker.sock' \
        || die "Docker socket not mounted in ${AGENTS_CONTAINER}. Add '-v /var/run/docker.sock:/var/run/docker.sock' in compose."

    # Ensure log dir
    mkdir -p "$LOG_DIR"
    green "  OK"
}

# ─── DSN derivation ──────────────────────────────────────────────────────
derive_dsn() {
    blue "[2/5] Deriving DSN from .env..."
    set -a; . "${REPO_DIR}/.env"; set +a
    local pwd_var="${DATALAKE_POSTGRES_ROOT_PASSWORD:-}"
    [ -n "$pwd_var" ] || die "DATALAKE_POSTGRES_ROOT_PASSWORD missing in .env"
    # Internal Docker network DNS: agents-platform → datalake-db:5432
    DSN="postgres://postgres:${pwd_var}@datalake-db:5432/datalake"
    green "  OK (datalake-db:5432/datalake as postgres)"
}

# ─── Pull / refresh Maigret image ────────────────────────────────────────
pull_maigret() {
    blue "[3/5] Refreshing soxoj/maigret:latest..."
    docker pull soxoj/maigret:latest 2>&1 | tail -3
    green "  OK"
}

# ─── Status: how many enriched / pending ─────────────────────────────────
show_status() {
    blue "[*] OSINT status:"
    docker exec "${DATALAKE_CONTAINER}" psql -U postgres -d datalake -t -A -F'|' <<'SQL'
SELECT 'enriched_total', count(*) FROM bronze.osint_persons;
SELECT 'with_linkedin', count(*) FROM bronze.osint_persons WHERE linkedin_urls IS NOT NULL AND array_length(linkedin_urls, 1) > 0;
SELECT 'with_github', count(*) FROM bronze.osint_persons WHERE github_usernames IS NOT NULL AND array_length(github_usernames, 1) > 0;
SELECT 'with_twitter', count(*) FROM bronze.osint_persons WHERE twitter_handles IS NOT NULL AND array_length(twitter_handles, 1) > 0;
SELECT 'last_24h', count(*) FROM bronze.osint_persons WHERE last_scanned_at > now() - interval '24 hours';
SELECT 'last_7d', count(*) FROM bronze.osint_persons WHERE last_scanned_at > now() - interval '7 days';
SQL
}

# ─── Run orchestrator ────────────────────────────────────────────────────
run_orchestrator() {
    local limit="$1"
    local with_holehe="${2:-false}"
    local extra_args=""
    [ "$with_holehe" = "true" ] && extra_args="--with-holehe"

    blue "[4/5] Launching orchestrator (limit=${limit}, holehe=${with_holehe})..."
    yellow "  Logs: ${LOG_FILE}"

    local started_at; started_at=$(date +%s)

    # Run inside agents-platform (it has python + psycopg + docker socket access)
    docker exec \
        -e "DSN=${DSN}" \
        "${AGENTS_CONTAINER}" \
        python3 "/app/${ORCHESTRATOR_REL_PATH#infrastructure/agents/}" \
            --limit "$limit" \
            --top-sites 50 \
            $extra_args 2>&1 | tee "$LOG_FILE"

    local elapsed=$(( $(date +%s) - started_at ))
    blue "[5/5] Done in ${elapsed}s. Log: ${LOG_FILE}"
}

# ─── Mode dispatcher ─────────────────────────────────────────────────────
mode="${1:-help}"

case "$mode" in
    test)
        preflight
        derive_dsn
        pull_maigret
        run_orchestrator 5 false
        show_status
        ;;
    batch)
        preflight
        derive_dsn
        run_orchestrator 500 false
        show_status
        ;;
    aggressive)
        preflight
        derive_dsn
        run_orchestrator 2000 false
        show_status
        ;;
    holehe)
        preflight
        derive_dsn
        run_orchestrator 100 true
        show_status
        ;;
    status)
        show_status
        ;;
    help|--help|-h|"")
        cat <<EOF
Maigret OSINT enrichment runner — DEMOEMA

Usage:
  $0 test        Validation setup, --limit 5 (~3 min)
  $0 batch       Run nocturne standard, --limit 500 (~5h)
  $0 aggressive  Rattrapage manuel, --limit 2000 (~20h)
  $0 holehe      Avec emails Holehe, --limit 100 (~10 min)
  $0 status      Stats bronze.osint_persons (no run)

Env vars:
  REPO_DIR       Path to DEMOEMA repo (default: /root/DEMOEMA)

Logs: /var/log/osint/maigret_*.log

Pour cron nocturne automatique :
  ./install_osint_cron.sh
EOF
        ;;
    *)
        die "Unknown mode: $mode (use --help)"
        ;;
esac
