#!/usr/bin/env bash
# DEMOEMA — migration de l'état d'un VPS source vers un VPS cible.
#
# Lance depuis ta machine LOCALE (pas depuis un VPS). Le script utilise
# ta clé SSH pour rebondir sur les 2 hosts via pipe. Aucun secret n'est
# exposé via stdout du shell local — tout passe en pipe SSH chiffré.
#
# Usage :
#   ./migrate-vps.sh \
#       --source root@OLD_HOST \
#       --target root@NEW_HOST \
#       [--ssh-key ~/.ssh/demoema_ionos_ed25519] \
#       [--phase env|datalake|all] \
#       [--dry-run]
#
# Phases :
#   1. env       — copie /root/DEMOEMA/.env source → target via pipe SSH
#                  (pas de fichier intermédiaire, pas d'exposition transcript)
#   2. datalake  — pg_dump source → pg_restore target via pipe SSH chiffré
#                  (avant : ALTER USER sur target pour matcher passwords source)
#   3. all       — env puis datalake (default)
#
# Pré-requis :
# - Le VPS target a déjà tourné `bootstrap-vps.sh` une fois (datalake-db existe).
# - La clé SSH a accès root aux 2 VPS.
# - Les 2 VPSes ont des Postgres compatibles (même major version, ici 16-alpine).
#
# Sécurité :
# - Le .env source contient TOUS les secrets prod. Le pipe SSH chiffre le
#   transfert. Le contenu n'apparaît JAMAIS sur stdout local.
# - pg_dump/pg_restore en custom format, sans owner/acl pour éviter les
#   conflits de roles entre source et target.
# - --clean --if-exists côté restore : drop puis recrée (idempotent si la
#   target avait déjà une partie des tables, ce qui est attendu après bootstrap).

set -euo pipefail

# ─── Args ──────────────────────────────────────────────────────────
SOURCE=""
TARGET=""
SSH_KEY="${SSH_KEY:-$HOME/.ssh/demoema_ionos_ed25519}"
PHASE="all"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --source) SOURCE="$2"; shift 2 ;;
        --target) TARGET="$2"; shift 2 ;;
        --ssh-key) SSH_KEY="$2"; shift 2 ;;
        --phase) PHASE="$2"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        -h|--help)
            grep '^#' "$0" | head -40
            exit 0
            ;;
        *) echo "Unknown arg: $1" >&2; exit 1 ;;
    esac
done

[ -n "$SOURCE" ] || { echo "ERROR: --source root@HOST required" >&2; exit 1; }
[ -n "$TARGET" ] || { echo "ERROR: --target root@HOST required" >&2; exit 1; }
[ -f "$SSH_KEY" ] || { echo "ERROR: SSH key not found: $SSH_KEY" >&2; exit 1; }

SSH_OPTS="-i $SSH_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30"

log() { echo "[migrate] $*" >&2; }
run() {
    if [ "$DRY_RUN" = "1" ]; then
        echo "DRY-RUN: $*"
    else
        eval "$@"
    fi
}

# ─── Phase: env ────────────────────────────────────────────────────
phase_env() {
    log "phase env : copie /root/DEMOEMA/.env de $SOURCE vers $TARGET"
    log "(le contenu reste dans le pipe SSH chiffré, pas dans le shell local)"
    run "ssh $SSH_OPTS $SOURCE 'cat /root/DEMOEMA/.env' | \
         ssh $SSH_OPTS $TARGET 'cat > /root/DEMOEMA/.env && chmod 600 /root/DEMOEMA/.env && wc -l /root/DEMOEMA/.env'"
}

# ─── Phase: datalake ───────────────────────────────────────────────
phase_datalake() {
    log "phase datalake : pg_dump $SOURCE → pg_restore $TARGET via pipe SSH"

    # 1. ALTER USER sur target pour matcher les passwords source.
    # Le target a été initialisé par bootstrap-vps.sh avec des passwords
    # aléatoires différents. Sans cette étape, le pg_restore depuis source
    # crée des données mais l'auth depuis agents-platform échouera.
    log "1/3 — ALTER USER postgres sur $TARGET pour matcher le password de $SOURCE"
    run "ssh $SSH_OPTS $TARGET '
        set -e
        PG_ROOT=\$(grep \"^DATALAKE_POSTGRES_ROOT_PASSWORD=\" /root/DEMOEMA/.env | cut -d= -f2)
        if [ -z \"\$PG_ROOT\" ]; then
            echo \"ERROR: DATALAKE_POSTGRES_ROOT_PASSWORD vide dans .env target\" >&2
            exit 1
        fi
        docker exec demomea-datalake-db psql -U postgres -d datalake -c \"ALTER USER postgres WITH PASSWORD \$\$\${PG_ROOT}\$\$\"
    '"

    # 2. pg_dump | pg_restore en pipe direct entre les 2 VPSes via le local
    # comme relay. -Fc = custom format (compressé). --no-owner --no-acl pour
    # éviter les conflits de roles. --clean --if-exists côté restore drop
    # les tables existantes (init scripts de bootstrap) avant recréation.
    log "2/3 — pg_dump $SOURCE → pg_restore $TARGET (durée : 30-90 min selon volume)"
    run "ssh $SSH_OPTS $SOURCE 'docker exec demomea-datalake-db pg_dump -U postgres -d datalake -Fc --no-owner --no-acl' \
         | ssh $SSH_OPTS $TARGET 'docker exec -i demomea-datalake-db pg_restore -U postgres -d datalake --no-owner --no-acl --clean --if-exists --jobs=1 2>&1 | tail -20'"

    # 3. Verify : compter les MV silver sur target (doit matcher source)
    log "3/3 — verification sur $TARGET"
    run "ssh $SSH_OPTS $TARGET 'docker exec demomea-datalake-db psql -U postgres -d datalake -c \"SELECT count(*) AS n_silvers FROM pg_matviews WHERE schemaname = '\\''silver'\\''\"'"

    # 4. Restart agents-platform pour reconnecter avec la DSN
    log "4/4 — restart agents-platform sur $TARGET pour reconnecter à la DB restorée"
    run "ssh $SSH_OPTS $TARGET 'docker restart demomea-agents-platform >/dev/null && sleep 8 && docker exec demomea-agents-platform sh -c \"curl -sf http://localhost:8100/healthz\"'"
}

# ─── Run ───────────────────────────────────────────────────────────
case "$PHASE" in
    env) phase_env ;;
    datalake) phase_datalake ;;
    all) phase_env; phase_datalake ;;
    *) echo "ERROR: unknown phase '$PHASE'" >&2; exit 1 ;;
esac

log "✅ phase $PHASE terminée"
