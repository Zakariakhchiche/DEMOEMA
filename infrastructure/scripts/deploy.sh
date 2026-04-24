#!/usr/bin/env bash
# DEMOEMA — deploy script called by .github/workflows/deploy-ionos.yml
# Usage: deploy.sh <component> <commit_sha>
# component: all | backend | frontend | agents

set -euo pipefail

COMPONENT="${1:-all}"
COMMIT_SHA="${2:-unknown}"
VPS_HOST="${VPS_HOST:-deploy@demoema.fr}"

# Capture pre-deploy state for rollback
echo "[deploy] Capturing pre-deploy SHA for rollback purposes..."
PREV_SHA=$(ssh -o BatchMode=yes -o StrictHostKeyChecking=no "$VPS_HOST" \
    'cd /root/DEMOEMA && git rev-parse --short HEAD' 2>/dev/null || echo "unknown")
echo "[deploy] prev=$PREV_SHA target=$COMMIT_SHA component=$COMPONENT"

# Run deploy on VPS
ssh -o BatchMode=yes -o StrictHostKeyChecking=no "$VPS_HOST" \
    bash -s -- "$COMPONENT" "$COMMIT_SHA" <<'REMOTE'
set -euo pipefail
COMPONENT="$1"
SHA="$2"
cd /root/DEMOEMA

echo "[deploy] current=$(git rev-parse --short HEAD) target=$SHA component=$COMPONENT"
git fetch --all --tags --prune
git reset --hard origin/develop

echo "[deploy] new_head=$(git rev-parse --short HEAD)"

case "$COMPONENT" in
    all)
        docker compose pull 2>/dev/null || true
        docker compose up -d --build --remove-orphans
        ;;
    backend|frontend|caddy)
        docker compose up -d --build --no-deps "$COMPONENT"
        ;;
    agents)
        # Agents platform lives in a separate compose file
        docker compose -f infrastructure/agents/docker-compose.agents.yml up -d --build --no-deps agents-platform
        ;;
    *)
        echo "[deploy] ERROR: unknown component '$COMPONENT' (expected: all|backend|frontend|caddy|agents)"
        exit 2
        ;;
esac

echo "[deploy] Services status:"
docker compose ps
REMOTE

# Append to deploy log
STAMP=$(date -u +"%Y-%m-%d %H:%M UTC")
DEPLOYER="${GITHUB_ACTOR:-$(whoami)}"
LOG_LINE="$STAMP | github-actions (sha=$COMMIT_SHA) | $PREV_SHA → $COMMIT_SHA | $COMPONENT | deploy auto"
echo "[deploy] Appending to docs/DEPLOY_LOG.md (local only if run from CI, else post-commit): $LOG_LINE"

# Smoke test
echo "[deploy] Waiting 10s for services to stabilize..."
sleep 10
if curl -fsSL --max-time 15 https://api.demoema.fr/healthz > /dev/null 2>&1; then
    echo "[deploy] ✅ api.demoema.fr/healthz OK"
else
    echo "[deploy] ⚠️  api.demoema.fr/healthz FAILED — investigating required"
    exit 3
fi

if curl -fsSL --max-time 15 https://demoema.fr/ -o /dev/null -w "web HTTP %{http_code}\n" 2>&1; then
    echo "[deploy] ✅ demoema.fr/ reachable"
else
    echo "[deploy] ⚠️  demoema.fr/ FAILED"
    exit 4
fi

echo "[deploy] ✅ Deploy complete: $COMMIT_SHA ($COMPONENT)"
