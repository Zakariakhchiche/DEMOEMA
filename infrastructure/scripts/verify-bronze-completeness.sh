#!/usr/bin/env bash
# DEMOEMA — wrapper qui lance verify_bronze_completeness.py sur un VPS.
#
# Le script Python est dans backend/agents/platform et a accès aux modules
# sources/* — il import chaque module et appelle count_upstream() quand
# défini, compare avec count(*) bronze, classe par status.
#
# Usage :
#   ./verify-bronze-completeness.sh --target root@HOST [--ssh-key KEY]
#
# Output :
#   stdout : JSON avec une entrée par source (parsable CI/script)
#   stderr : rapport tabulaire lisible humain (catégorisé ✅/⚠️/❌/ℹ️)
#
# Exit code :
#   0 = tout OK ou no_upstream uniquement
#   1 = au moins une source partial, empty ou table_missing
#   2 = erreur d'exécution

set -euo pipefail

TARGET=""
SSH_KEY="${SSH_KEY:-$HOME/.ssh/demoema_ionos_ed25519}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target) TARGET="$2"; shift 2 ;;
        --ssh-key) SSH_KEY="$2"; shift 2 ;;
        -h|--help) grep '^#' "$0" | head -20; exit 0 ;;
        *) echo "Unknown arg: $1" >&2; exit 1 ;;
    esac
done

[ -n "$TARGET" ] || { echo "ERROR: --target required" >&2; exit 1; }

SSH_OPTS="-i $SSH_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"

# Le script Python tourne DANS le container agents-platform pour avoir accès :
# - aux variables d'env (DATABASE_URL via Pydantic Settings)
# - aux modules ingestion/sources/*.py
# - à la dépendance httpx pour les count_upstream() qui font des HTTP calls
#
# `python -m verify_bronze_completeness` (au lieu de `python verify...py`)
# pour que les imports relatifs (ingestion.sources.X) fonctionnent.

ssh $SSH_OPTS "$TARGET" "docker exec demomea-agents-platform python -m verify_bronze_completeness"
