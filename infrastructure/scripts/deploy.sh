#!/usr/bin/env bash
# DEMOEMA — deploy script called by .github/workflows/deploy-ionos.yml
# Usage: deploy.sh <component> <commit_sha>
# component: all | backend | frontend | caddy | agents
#
# Resilient design : aucun chemin codé en dur (REPO_DIR override possible),
# les smoke tests publics sont informatifs (l'agent-platform interne est
# le critère canonique de succès du déploiement). Permet la migration VPS
# avant que le DNS public ne soit configuré.

set -euo pipefail

COMPONENT="${1:-all}"
COMMIT_SHA="${2:-unknown}"
VPS_HOST="${VPS_HOST:-root@82.165.242.205}"
REPO_DIR="${REPO_DIR:-/root/DEMOEMA}"
PUBLIC_API_URL="${PUBLIC_API_URL:-https://api.demoema.fr/healthz}"
PUBLIC_WEB_URL="${PUBLIC_WEB_URL:-https://demoema.fr/}"

echo "[deploy] target=$VPS_HOST repo=$REPO_DIR component=$COMPONENT sha=$COMMIT_SHA"

# Pre-deploy: capture rollback SHA (best-effort)
PREV_SHA=$(ssh -o BatchMode=yes -o StrictHostKeyChecking=no "$VPS_HOST" \
    "cd $REPO_DIR && git rev-parse --short HEAD" 2>/dev/null || echo "unknown")
echo "[deploy] prev=$PREV_SHA"

# Run deploy on VPS — the heredoc receives REPO_DIR via the -- args so the
# remote side stays config-free. `set -e` ensures any failed step aborts.
ssh -o BatchMode=yes -o StrictHostKeyChecking=no "$VPS_HOST" \
    bash -s -- "$COMPONENT" "$COMMIT_SHA" "$REPO_DIR" <<'REMOTE'
set -euo pipefail
COMPONENT="$1"
SHA="$2"
REPO_DIR="$3"
cd "$REPO_DIR"

AGENTS_COMPOSE="infrastructure/agents/docker-compose.agents.yml"

echo "[remote] current=$(git rev-parse --short HEAD) target=$SHA component=$COMPONENT cwd=$(pwd)"

# Stash any local changes (notably the .env's CRLF/LF normalization that
# autocrlf may have introduced) so the reset can land cleanly. Git will
# auto-restore via stash list — no data loss, just gives the reset a clean
# tree to land on.
if [ -n "$(git status --porcelain)" ]; then
    git stash push -m "auto-deploy-$(date +%Y%m%dT%H%M%SZ)" --include-untracked || true
fi
git fetch origin --prune
git reset --hard origin/main
echo "[remote] new_head=$(git rev-parse --short HEAD)"

# Make sure the agents compose finds its env file (symlink to root .env).
# Idempotent : ne touche pas si déjà en place.
if [ -f "$REPO_DIR/.env" ] && [ ! -e "$REPO_DIR/infrastructure/agents/.env" ]; then
    ln -sf "$REPO_DIR/.env" "$REPO_DIR/infrastructure/agents/.env"
fi

deploy_main() {
    docker compose up -d --build --remove-orphans
}

deploy_agents() {
    docker compose -f "$AGENTS_COMPOSE" up -d --build --remove-orphans agents-platform
}

case "$COMPONENT" in
    all)
        # `all` redéploie LES DEUX stacks. L'oubli historique des agents dans
        # ce branch a fait que les fixes silver de la matinée du 27/04 ne
        # sont jamais arrivés en prod via auto-deploy.
        deploy_main
        deploy_agents
        ;;
    backend|frontend|caddy)
        docker compose up -d --build --no-deps "$COMPONENT"
        ;;
    agents)
        deploy_agents
        ;;
    *)
        echo "[remote] ERROR: unknown component '$COMPONENT' (expected: all|backend|frontend|caddy|agents)"
        exit 2
        ;;
esac

echo "[remote] services :"
docker compose ps 2>/dev/null || true
docker compose -f "$AGENTS_COMPOSE" ps 2>/dev/null || true

# Smoke test interne (canonique) — agents-platform expose /healthz sur 8100.
# Tape directement le container pour ne pas dépendre du DNS public ni de Caddy.
echo "[remote] attente stabilisation 8s puis smoke interne..."
sleep 8
INTERNAL_OK=0
for attempt in 1 2 3 4 5; do
    if docker exec demomea-agents-platform sh -c \
        'curl -fsSL --max-time 5 http://localhost:8100/healthz' >/dev/null 2>&1; then
        INTERNAL_OK=1
        echo "[remote] ✅ agents-platform /healthz interne OK"
        break
    fi
    echo "[remote] healthz attempt $attempt failed, retry in 4s..."
    sleep 4
done
if [ "$INTERNAL_OK" != "1" ]; then
    echo "[remote] ❌ agents-platform /healthz interne KO après 5 essais"
    docker logs --tail=80 demomea-agents-platform 2>&1 | tail -40 || true
    exit 3
fi
REMOTE

# Smoke tests publics — informatif uniquement. Le DNS / Caddy peut être
# pas encore configuré (cas migration VPS) sans que cela invalide le déploiement.
echo "[deploy] smoke tests publics (informatif) :"
if curl -fsSL --max-time 10 "$PUBLIC_API_URL" >/dev/null 2>&1; then
    echo "[deploy] ✅ $PUBLIC_API_URL atteignable"
else
    echo "[deploy] ℹ️  $PUBLIC_API_URL injoignable — DNS/Caddy pas configuré ?"
fi
if curl -fsSL --max-time 10 "$PUBLIC_WEB_URL" -o /dev/null -w "[deploy] web HTTP %{http_code}\n" 2>&1; then
    :
else
    echo "[deploy] ℹ️  $PUBLIC_WEB_URL injoignable — informatif"
fi

echo "[deploy] ✅ Deploy complete: $COMMIT_SHA ($COMPONENT)"
