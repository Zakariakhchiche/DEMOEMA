#!/usr/bin/env bash
set -euo pipefail

# Script d'install à exécuter UNE FOIS sur le VPS Ubuntu 24.04 fraîchement provisionné.
# Usage (en root ou sudo) :
#   curl -fsSL https://raw.githubusercontent.com/<user>/<repo>/main/deploy.sh | bash
# ou après git clone :
#   sudo bash deploy.sh

if [[ $EUID -ne 0 ]]; then
    echo "Relance avec sudo." >&2
    exit 1
fi

echo "==> Mise à jour du système"
apt-get update -y
apt-get upgrade -y

echo "==> Paquets de base"
apt-get install -y ca-certificates curl gnupg git ufw fail2ban unattended-upgrades

echo "==> Installation Docker"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "==> Firewall UFW"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> fail2ban"
systemctl enable --now fail2ban

echo "==> Mises à jour auto (sécurité)"
dpkg-reconfigure -f noninteractive unattended-upgrades

echo "==> Terminé."
echo "Prochaines étapes :"
echo "  1) cp .env.example .env && nano .env     # remplir les secrets"
echo "  2) docker compose build"
echo "  3) docker compose up -d"
echo "  4) docker compose logs -f"
