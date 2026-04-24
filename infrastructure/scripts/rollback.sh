#!/usr/bin/env bash
# DEMOEMA — rollback script
# Usage: rollback.sh <target_sha>
#
# Resets the VPS git checkout to <target_sha> and rebuilds containers.
# See docs/RUNBOOK_ROLLBACK.md for the full procedure.

set -euo pipefail

TARGET_SHA="${1:-}"
VPS_HOST="${VPS_HOST:-deploy@demoema.fr}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"

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
    'cd /root/DEMOEMA && git rev-parse --short HEAD' 2>/dev/null || echo "unknown")
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

# Run rollback on VPS
ssh -i "$SSH_KEY" -o BatchMode=yes "$VPS_HOST" \
    bash -s -- "$TARGET_SHA" <<'REMOTE'
set -euo pipefail
SHA="$1"
cd /root/DEMOEMA

echo "[rollback] Current HEAD: $(git rev-parse --short HEAD)"
echo "[rollback] Target:       $SHA"

# Resolve SHA (supports HEAD~N, short SHA, full SHA)
RESOLVED=$(git rev-parse --short "$SHA")
echo "[rollback] Resolved target: $RESOLVED"

# Fetch latest refs (in case target is on a different branch)
git fetch --all --tags

# Hard reset
git reset --hard "$RESOLVED"

echo "[rollback] New HEAD: $(git rev-parse --short HEAD)"

# Rebuild all services
docker compose up -d --build --remove-orphans

echo "[rollback] Services status:"
docker compose ps

REMOTE

# Smoke test
echo "[rollback] Waiting 10s for services to stabilize..."
sleep 10

if curl -fsSL --max-time 15 https://api.demoema.fr/healthz > /dev/null 2>&1; then
    echo "[rollback] ✅ api.demoema.fr/healthz OK"
else
    echo "[rollback] ❌ api.demoema.fr/healthz FAILED — VPS in unknown state, escalate to Zak immediately"
    exit 10
fi

if curl -fsSL --max-time 15 https://demoema.fr/ -o /dev/null; then
    echo "[rollback] ✅ demoema.fr/ reachable"
else
    echo "[rollback] ⚠️  demoema.fr/ FAILED"
    exit 11
fi

STAMP=$(date -u +"%Y-%m-%d %H:%M UTC")
echo "[rollback] ✅ Rollback complete: $CURRENT_SHA → $TARGET_SHA at $STAMP"
echo ""
echo "Next steps:"
echo "  1. Edit docs/DEPLOY_LOG.md to append: '$STAMP | rollback-manual | $CURRENT_SHA → $TARGET_SHA | all | ROLLBACK'"
echo "  2. Edit docs/DEPLOY_LOG.md to mark the source deploy '[ROLLED BACK at $STAMP]'"
echo "  3. Open INC-YYYY-NNNN in docs/INCIDENTS.md"
echo "  4. Notify Slack #demoema-ops or davyly1@gmail.com"
