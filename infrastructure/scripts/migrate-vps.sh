#!/usr/bin/env bash
# DEMOEMA — migration VPS → VPS direct (sans transit local).
#
# Lance depuis ta machine LOCALE, mais le transfert de données passe DIRECT
# entre les 2 VPS via SSH. Ta machine sert juste à orchestrer.
#
# Le script :
#  1. Génère une clé éphémère sur le TARGET (~/.ssh/migration_key)
#  2. Pousse sa pubkey dans authorized_keys du SOURCE (via ton ssh local)
#  3. Test target → source SSH
#  4. Pipe `ssh source "pg_dump" | pg_restore` SUR LE TARGET (= VPS-to-VPS)
#  5. Cleanup : retire la clé éphémère du source authorized_keys
#
# Aucune donnée datalake ne traverse ta machine. Seuls le SQL ALTER USER
# et la commande de pipe SSH transitent (1-2 KB).
#
# Usage :
#   ./migrate-vps.sh \
#       --source root@OLD_HOST \
#       --target root@NEW_HOST \
#       [--ssh-key ~/.ssh/demoema_ionos_ed25519] \
#       [--phase env|datalake|all|cleanup-key] \
#       [--dry-run]
#
# Phases :
#   env       — copie /root/DEMOEMA/.env source → target via pipe SSH
#               (passe par local mais en pipe chiffré, jamais sur disque)
#   datalake  — pg_dump source → pg_restore target (VPS-to-VPS direct)
#   cleanup-key — retire la clé éphémère du source authorized_keys
#   all       — env puis datalake puis cleanup-key (default)

set -euo pipefail

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
SOURCE_HOST="${SOURCE#*@}"   # extract hostname for known_hosts on target
TARGET_MIG_KEY="/root/.ssh/migration_key"

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

# ─── Phase: bootstrap clé migration target → source ───────────────
phase_setup_target_to_source_key() {
    log "setup : clé éphémère target → source pour transfert VPS-to-VPS"
    # 1. Générer keypair sur target (idempotent — ne touche pas si existe)
    run "ssh $SSH_OPTS $TARGET '
        if [ ! -f $TARGET_MIG_KEY ]; then
            ssh-keygen -t ed25519 -N \"\" -C migration-key -f $TARGET_MIG_KEY -q
            echo \"created $TARGET_MIG_KEY\"
        fi
        cat $TARGET_MIG_KEY.pub
    '" > /tmp/_migration_pub.tmp

    if [ "$DRY_RUN" = "1" ]; then
        rm -f /tmp/_migration_pub.tmp
        return 0
    fi

    PUBKEY=$(tail -1 /tmp/_migration_pub.tmp)
    rm -f /tmp/_migration_pub.tmp
    [ -n "$PUBKEY" ] || { echo "ERROR: pubkey vide" >&2; exit 1; }

    # 2. Push pubkey vers source authorized_keys (idempotent)
    log "push pubkey target → source authorized_keys"
    run "ssh $SSH_OPTS $SOURCE 'mkdir -p ~/.ssh && chmod 700 ~/.ssh && \
         grep -qF \"$PUBKEY\" ~/.ssh/authorized_keys 2>/dev/null \
           || echo \"$PUBKEY\" >> ~/.ssh/authorized_keys && \
         chmod 600 ~/.ssh/authorized_keys && wc -l ~/.ssh/authorized_keys'"

    # 3. Test target → source SSH
    log "test SSH target → source"
    run "ssh $SSH_OPTS $TARGET 'ssh -i $TARGET_MIG_KEY -o IdentitiesOnly=yes \
         -o StrictHostKeyChecking=accept-new $SOURCE \"echo OK direct VPS-to-VPS\"'"
}

# ─── Phase: cleanup-key (retire la clé éphémère du source) ──────────
phase_cleanup_key() {
    log "cleanup : retire la clé éphémère du source authorized_keys"
    run "ssh $SSH_OPTS $TARGET 'cat $TARGET_MIG_KEY.pub 2>/dev/null'" > /tmp/_migration_pub.tmp || true

    if [ "$DRY_RUN" = "1" ] || [ ! -s /tmp/_migration_pub.tmp ]; then
        rm -f /tmp/_migration_pub.tmp
        log "(rien à nettoyer — clé migration absente sur target ou dry-run)"
        return 0
    fi

    PUBKEY=$(tail -1 /tmp/_migration_pub.tmp)
    rm -f /tmp/_migration_pub.tmp

    # Retire la ligne du authorized_keys du source
    run "ssh $SSH_OPTS $SOURCE \"grep -vF '$PUBKEY' ~/.ssh/authorized_keys > ~/.ssh/authorized_keys.tmp && \
         mv ~/.ssh/authorized_keys.tmp ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && \
         wc -l ~/.ssh/authorized_keys\""

    log "✅ clé éphémère retirée du source"
}

# ─── Phase: datalake (VPS-to-VPS direct) ───────────────────────────
phase_datalake() {
    phase_setup_target_to_source_key

    # 1. ALTER USER postgres sur target pour matcher le password source.
    # Helper Python (évite l'enfer du triple-escape bash→ssh→psql).
    log "1/4 — ALTER USER postgres sur $TARGET pour matcher le password de $SOURCE"
    run "ssh $SSH_OPTS $TARGET 'python3 - <<PYEOF
import subprocess, sys
pwd = \"\"
with open(\"/root/DEMOEMA/.env\") as f:
    for line in f:
        if line.startswith(\"DATALAKE_POSTGRES_ROOT_PASSWORD=\"):
            pwd = line.split(\"=\", 1)[1].strip()
            break
if not pwd:
    sys.exit(\"DATALAKE_POSTGRES_ROOT_PASSWORD missing\")
pwd_escaped = pwd.replace(\"\\x27\", \"\\x27\\x27\")
sql = f\"ALTER USER postgres WITH PASSWORD \\x27{pwd_escaped}\\x27;\"
r = subprocess.run([\"docker\", \"exec\", \"-i\", \"demomea-datalake-db\",
                    \"psql\", \"-U\", \"postgres\", \"-d\", \"datalake\"],
                   input=sql, text=True, capture_output=True)
print(r.stdout)
if r.returncode != 0:
    sys.stderr.write(r.stderr)
    sys.exit(r.returncode)
PYEOF'"

    # 2. pg_dump source → pg_restore target — exécuté SUR le target
    # qui SSH directement vers source. Aucune donnée ne passe par local.
    # -Fc = custom format (compressé). --no-owner --no-acl ignore les role
    # specifics. --clean --if-exists drop les tables avant restore (target
    # avait des schemas vides post-bootstrap).
    log "2/4 — pg_dump $SOURCE → pg_restore $TARGET (VPS-to-VPS, durée 30-90 min)"
    run "ssh $SSH_OPTS $TARGET '
        ssh -i $TARGET_MIG_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=no \
            -o ServerAliveInterval=30 $SOURCE \
            \"docker exec demomea-datalake-db pg_dump -U postgres -d datalake -Fc --no-owner --no-acl\" \
        | docker exec -i demomea-datalake-db pg_restore -U postgres -d datalake \
            --no-owner --no-acl --clean --if-exists --jobs=1 2>&1 | tail -20
    '"

    log "3/4 — vérification count silver MV sur $TARGET"
    run "ssh $SSH_OPTS $TARGET 'docker exec demomea-datalake-db psql -U postgres -d datalake -c \"SELECT count(*) AS n_silvers FROM pg_matviews WHERE schemaname = '\\''silver'\\''\"'"

    log "4/4 — restart agents-platform sur $TARGET"
    run "ssh $SSH_OPTS $TARGET 'docker restart demomea-agents-platform >/dev/null && sleep 8 && docker exec demomea-agents-platform sh -c \"curl -sf http://localhost:8100/healthz\"'"
}

case "$PHASE" in
    env) phase_env ;;
    datalake) phase_datalake ;;
    cleanup-key) phase_cleanup_key ;;
    all) phase_env; phase_datalake; phase_cleanup_key ;;
    *) echo "ERROR: unknown phase '$PHASE'" >&2; exit 1 ;;
esac

log "✅ phase $PHASE terminée"
