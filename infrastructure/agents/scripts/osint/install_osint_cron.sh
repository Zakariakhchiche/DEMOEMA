#!/usr/bin/env bash
# ============================================================================
# Installer du timer systemd pour l'OSINT enrichment Maigret nocturne.
#
# Crée :
#   /etc/systemd/system/osint-maigret.service  -- exécute run_maigret_osint.sh batch
#   /etc/systemd/system/osint-maigret.timer    -- lance chaque jour à 02:00
#
# Usage : ./install_osint_cron.sh           # install + enable
#         ./install_osint_cron.sh uninstall # disable + remove
#         ./install_osint_cron.sh status    # show timer status
# ============================================================================
set -euo pipefail

REPO_DIR="${REPO_DIR:-/root/DEMOEMA}"
SCRIPT_PATH="${REPO_DIR}/infrastructure/agents/scripts/osint/run_maigret_osint.sh"
SERVICE_NAME="osint-maigret"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
TIMER_FILE="/etc/systemd/system/${SERVICE_NAME}.timer"

red()    { printf "\033[31m%s\033[0m\n" "$*" >&2; }
green()  { printf "\033[32m%s\033[0m\n" "$*"; }
blue()   { printf "\033[34m%s\033[0m\n" "$*"; }

die() { red "ERROR: $*"; exit 1; }

[ "$(id -u)" -eq 0 ] || die "Must run as root (sudo)"

cmd="${1:-install}"

case "$cmd" in
    install)
        [ -f "$SCRIPT_PATH" ] || die "$SCRIPT_PATH not found. Run from VPS with repo cloned."
        chmod +x "$SCRIPT_PATH"

        blue "[1/3] Writing service unit..."
        cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=DEMOEMA OSINT Maigret enrichment (nightly batch)
After=docker.service network-online.target
Wants=docker.service network-online.target

[Service]
Type=oneshot
Environment=REPO_DIR=${REPO_DIR}
ExecStart=${SCRIPT_PATH} batch
StandardOutput=journal
StandardError=journal
TimeoutStartSec=8h
EOF

        blue "[2/3] Writing timer unit (daily at 02:00)..."
        cat > "$TIMER_FILE" <<EOF
[Unit]
Description=DEMOEMA OSINT Maigret nightly timer
Requires=${SERVICE_NAME}.service

[Timer]
# Tous les jours à 02:00 heure VPS, randomisé +/- 30 min pour étaler la
# charge réseau (les sites Maigret throttle moins si on n'arrive pas pile).
OnCalendar=*-*-* 02:00:00
RandomizedDelaySec=30min
Persistent=true
Unit=${SERVICE_NAME}.service

[Install]
WantedBy=timers.target
EOF

        blue "[3/3] Reloading systemd + enabling timer..."
        systemctl daemon-reload
        systemctl enable --now "${SERVICE_NAME}.timer"
        green "OK"

        echo ""
        blue "Status :"
        systemctl status "${SERVICE_NAME}.timer" --no-pager | head -15
        echo ""
        green "Cron OSINT installé. Tournera chaque nuit ~02:00 (+/-30 min)."
        green "Logs : journalctl -u ${SERVICE_NAME}.service -f"
        green "       /var/log/osint/maigret_*.log"
        ;;

    uninstall)
        blue "Disabling + removing..."
        systemctl disable --now "${SERVICE_NAME}.timer" 2>/dev/null || true
        rm -f "$SERVICE_FILE" "$TIMER_FILE"
        systemctl daemon-reload
        green "OK — uninstalled."
        ;;

    status)
        echo "=== TIMER ==="
        systemctl status "${SERVICE_NAME}.timer" --no-pager 2>&1 | head -20
        echo ""
        echo "=== LAST RUN ==="
        systemctl status "${SERVICE_NAME}.service" --no-pager 2>&1 | head -20
        echo ""
        echo "=== NEXT TRIGGER ==="
        systemctl list-timers "${SERVICE_NAME}.timer" --no-pager 2>&1 | head -5
        ;;

    run-now)
        blue "Triggering immediate run..."
        systemctl start "${SERVICE_NAME}.service"
        echo ""
        echo "Follow with: journalctl -u ${SERVICE_NAME}.service -f"
        ;;

    *)
        cat <<EOF
Usage: $0 [install|uninstall|status|run-now]

  install     Crée + enable le timer systemd nocturne (chaque jour 02:00)
  uninstall   Disable + supprime le timer
  status      Affiche l'état timer + dernier run
  run-now     Force un run immédiat (sans attendre 02:00)
EOF
        ;;
esac
