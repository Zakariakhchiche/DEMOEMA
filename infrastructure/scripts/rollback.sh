#!/usr/bin/env bash
# DEMOEMA — rollback script
# Usage: rollback.sh <target_sha>
#
# Resets the VPS git checkout to <target_sha> and rebuilds containers.
# See docs/RUNBOOK_ROLLBACK.md for the full procedure.

set -euo pipefail

TARGET_SHA="${1:-}"
VPS_HOST="${VPS_HOST:-root@82.165.242.205}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/demoema_ionos_ed25519}"
REPO_DIR="${REPO_DIR:-/root/DEMOEMA}"

if [[ -z "$TARGET_SHA" ]]; then
    echo "usage: rollback.sh <target_sha>"
    echo ""
    echo "Examples:"
    echo "  rollback.sh abc1234         # rollback to specific short SHA"
    echo "  rollback.sh HEAD~1          # rollback one commit back"
    echo ""
    echo "See docs/DEPLOY_LOG.md for recent deploy SHAs."
    exit 1
fi

echo "[rollback] Target SHA: $TARGET_SHA"
echo "[rollback] VPS: $VPS_HOST"

# Capture current SHA for the log
CURRENT_SHA=$(ssh -i "$SSH_KEY" -o BatchMode=yes "$VPS_HOST" \
    "cd $REPO_DIR && git rev-parse --short HEAD" 2>/dev/null || echo "unknown")
echo "[rollback] Current SHA on VPS: $CURRENT_SHA"

# Confirmation prompt (skip if --yes flag or CI)
if [[ "${2:-}" != "--yes" && -z "${CI:-}" ]]; then
    echo ""
    echo "About to reset VPS /root/DEMOEMA from $CURRENT_SHA to $TARGET_SHA and rebuild all containers."
    read -p "Proceed? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "[rollback] Aborted."
        exit 0
    fi
fi

# Run rollback on VPS — same dual-stack rebuild que deploy.sh + smoke interne
ssh -i "$SSH_KEY" -o BatchMode=yes "$VPS_HOST" \
    bash -s -- "$TARGET_SHA" "$REPO_DIR" <<'REMOTE'
set -euo pipefail
SHA="$1"
REPO_DIR="$2"
cd "$REPO_DIR"

AGENTS_COMPOSE="infrastructure/agents/docker-compose.agents.yml"

echo "[rollback] current=$(git rev-parse --short HEAD) target=$SHA"

if [ -n "$(git status --porcelain)" ]; then
    git stash push -m "auto-rollback-$(date +%Y%m%dT%H%M%SZ)" --include-untracked || true
fi

RESOLVED=$(git rev-parse --short "$SHA")
echo "[rollback] resolved=$RESOLVED"

git fetch --all --tags
git reset --hard "$RESOLVED"
echo "[rollback] new_head=$(git rev-parse --short HEAD)"

# Rebuild les 2 stacks comme le fait deploy.sh — sinon agents-platform reste
# sur le code post-rollback divergent.
docker compose up -d --build --remove-orphans
docker compose -f "$AGENTS_COMPOSE" up -d --build --remove-orphans agents-platform

echo "[rollback] services :"
docker compose ps 2>/dev/null || true
docker compose -f "$AGENTS_COMPOSE" ps 2>/dev/null || true

# Smoke interne (canonique, même logique que deploy.sh)
sleep 8
INTERNAL_OK=0
for attempt in 1 2 3 4 5; do
    if docker exec demomea-agents-platform sh -c \
        'curl -fsSL --max-time 5 http://localhost:8100/healthz' >/dev/null 2>&1; then
        INTERNAL_OK=1
        echo "[rollback] ✅ agents-platform /healthz interne OK"
        break
    fi
    sleep 4
done
if [ "$INTERNAL_OK" != "1" ]; then
    echo "[rollback] ❌ agents-platform /healthz interne KO — état inconnu, escalader"
    exit 10
fi
REMOTE

# Smoke publics — informatifs (DNS peut ne pas être configuré en migration)
if curl -fsSL --max-time 10 https://api.demoema.fr/healthz >/dev/null 2>&1; then
    echo "[rollback] ✅ api.demoema.fr/healthz OK"
else
    echo "[rollback] ℹ️  api.demoema.fr injoignable (DNS pas configuré ?)"
fi

STAMP=$(date -u +"%Y-%m-%d %H:%M UTC")
echo "[rollback] ✅ Rollback complete: $CURRENT_SHA → $TARGET_SHA at $STAMP"
echo ""
echo "Next steps:"
echo "  1. Edit docs/DEPLOY_LOG.md to append: '$STAMP | rollback-manual | $CURRENT_SHA → $TARGET_SHA | all | ROLLBACK'"
echo "  2. Edit docs/DEPLOY_LOG.md to mark the source deploy '[ROLLED BACK at $STAMP]'"
echo "  3. Open INC-YYYY-NNNN in docs/INCIDENTS.md"
echo "  4. Notify Slack #demoema-ops or davyly1@gmail.com"
