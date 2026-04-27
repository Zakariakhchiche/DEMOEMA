#!/usr/bin/env bash
# DEMOEMA — bootstrap d'un VPS neuf en zéro-config.
#
# Idempotent : peut être ré-exécuté sans casser un VPS déjà bootstrappé. Si
# .env existe il est respecté, sinon il est généré avec des passwords aléatoires.
#
# Usage : ./bootstrap-vps.sh [--with-bronze]
#   --with-bronze   après le up, déclenche les ingestions bronze prioritaires
#
# Pré-requis sur la machine cible :
#   - docker + docker compose plugin
#   - le repo cloné dans /root/DEMOEMA (ou pwd = racine repo)
#   - infrastructure/agents/datalake-init/ contient les scripts initdb des rôles
#
# Ce que fait le script :
#   1. Vérifie docker / docker compose
#   2. Génère .env si absent (avec passwords openssl rand -hex 24)
#   3. Symlink .env -> infrastructure/agents/.env (compose attend ce path)
#   4. docker compose up des 2 stacks (principale + agents)
#   5. Attend datalake-db healthy
#   6. Vérifie que silver_engine.start_silver_scheduler a démarré côté agents
#   7. Affiche le statut de chaque service

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/root/DEMOEMA}"
ENV_FILE="$REPO_ROOT/.env"
AGENTS_ENV_LINK="$REPO_ROOT/infrastructure/agents/.env"
COMPOSE_AGENTS="$REPO_ROOT/infrastructure/agents/docker-compose.agents.yml"

log() { echo "[bootstrap] $*"; }
err() { echo "[bootstrap] ERROR: $*" >&2; exit 1; }

[ -d "$REPO_ROOT/.git" ] || err "REPO_ROOT=$REPO_ROOT n'est pas un repo git"
command -v docker >/dev/null || err "docker introuvable"
docker compose version >/dev/null 2>&1 || err "docker compose plugin introuvable"

cd "$REPO_ROOT"

# 1. .env (génère si absent ; complète si certains champs requis manquent)
gen_pwd() { openssl rand -hex 24; }

ensure_env_var() {
    local var="$1"
    local value="$2"
    if grep -q "^${var}=" "$ENV_FILE" && [ -n "$(grep "^${var}=" "$ENV_FILE" | head -1 | cut -d= -f2-)" ]; then
        return 0
    fi
    # Variable absente OU valeur vide → ajoute / remplace
    if grep -q "^${var}=" "$ENV_FILE"; then
        sed -i "s|^${var}=.*|${var}=${value}|" "$ENV_FILE"
        log "$var → mis à jour (valeur vide remplacée)"
    else
        echo "${var}=${value}" >> "$ENV_FILE"
        log "$var → ajouté"
    fi
}

if [ ! -f "$ENV_FILE" ]; then
    log ".env absent — génération initiale"
    cp "$REPO_ROOT/.env.example" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
fi

# Vars Postgres requises (zéro effet si déjà set)
ensure_env_var DATALAKE_POSTGRES_ROOT_PASSWORD "$(gen_pwd)"
ensure_env_var DATALAKE_AGENTS_PASSWORD "$(gen_pwd)"
ensure_env_var DATALAKE_RO_PASSWORD "$(gen_pwd)"
chmod 600 "$ENV_FILE"

# 2. Symlink que le compose des agents attend
if [ ! -L "$AGENTS_ENV_LINK" ] && [ ! -f "$AGENTS_ENV_LINK" ]; then
    ln -sf "$ENV_FILE" "$AGENTS_ENV_LINK"
    log "symlink créé : $AGENTS_ENV_LINK -> $ENV_FILE"
fi

# 3. Compose up
log "lancement docker compose (stack principale)"
docker compose up -d --remove-orphans

log "lancement docker compose agents-platform"
docker compose -f "$COMPOSE_AGENTS" up -d --build --remove-orphans

# 4. Attendre datalake-db healthy (max 60s)
log "attente datalake-db healthy..."
for i in $(seq 1 30); do
    state=$(docker inspect -f '{{.State.Health.Status}}' demomea-datalake-db 2>/dev/null || echo "unknown")
    if [ "$state" = "healthy" ]; then
        log "datalake-db healthy"
        break
    fi
    sleep 2
done

# 5. Vérifier que silver_engine a démarré (logs récents)
sleep 5
if docker logs demomea-agents-platform --since=30s 2>&1 | grep -q "Ingestion scheduler démarré"; then
    log "✅ silver_engine + bronze scheduler actifs"
elif docker logs demomea-agents-platform --since=30s 2>&1 | grep -q "DATABASE_URL vide"; then
    err "silver_engine NON DÉMARRÉ — DATABASE_URL non résolu côté container. Vérifie DATALAKE_POSTGRES_ROOT_PASSWORD dans $ENV_FILE."
else
    log "⚠️  silver_engine status indéterminé — check : docker logs demomea-agents-platform --tail 100"
fi

# 6. Statut final
log "=========================================="
log "Statut services :"
docker compose ps 2>/dev/null || true
docker compose -f "$COMPOSE_AGENTS" ps 2>/dev/null || true
log "=========================================="
log "Pour valider end-to-end : curl http://localhost:8100/healthz"
log "→ {\"status\":\"ok\",\"scheduler\":true,\"database_url_set\":true} attendu"
