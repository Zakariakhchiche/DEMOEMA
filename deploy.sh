#!/usr/bin/env bash
set -euo pipefail

# ===========================================================================
# Bootstrap VPS (Ubuntu 24.04) pour deployer DEMOEMA en Docker.
# Teste sur IONOS VPS L, Hetzner CX/CPX/CAX, OVH VPS, Contabo.
#
# Usage (en sudo) :
#   sudo bash deploy.sh
# ===========================================================================

if [[ $EUID -ne 0 ]]; then
    echo "Relance avec sudo." >&2
    exit 1
fi

echo "==> Detection de la taille du VPS"
TOTAL_MEM_MB=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
CPU_COUNT=$(nproc)
echo "    RAM totale : ${TOTAL_MEM_MB} MB"
echo "    vCPU       : ${CPU_COUNT}"

echo "==> Mise a jour du systeme"
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

echo "==> Config daemon Docker (rotation logs, live-restore, shutdown timeout)"
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "live-restore": true,
  "shutdown-timeout": 30
}
EOF
systemctl restart docker

echo "==> Swap (utile si RAM <= 8 GB)"
if [[ ${TOTAL_MEM_MB} -le 8192 ]] && [[ ! -f /swapfile ]]; then
    SWAP_SIZE_GB=4
    echo "    Creation d'un swapfile de ${SWAP_SIZE_GB} GB"
    fallocate -l ${SWAP_SIZE_GB}G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo "/swapfile none swap sw 0 0" >> /etc/fstab
    sysctl vm.swappiness=10 > /dev/null
    echo "vm.swappiness=10" > /etc/sysctl.d/99-swappiness.conf
else
    echo "    Skip (RAM > 8 GB ou swap deja present)"
fi

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

echo "==> Mises a jour auto (securite)"
dpkg-reconfigure -f noninteractive unattended-upgrades

echo ""
echo "==> Bootstrap termine."
echo ""
echo "Prochaines etapes :"
echo "  1) cp .env.example .env && nano .env"
echo "     Remplir DOMAIN, SUPABASE_*, MOTHERDUCK_TOKEN, AI_GATEWAY_API_KEY..."
echo "  2) docker compose build"
echo "  3) docker compose up -d"
echo "  4) docker compose logs -f caddy"
echo ""
echo "IMPORTANT IONOS : pensez a ouvrir les ports 80/443 aussi dans la"
echo "                 Cloud Firewall IONOS (panel > Reseau > Pare-feu),"
echo "                 en plus d'UFW ici. Par defaut IONOS bloque tout."
echo ""
echo "Le DNS A record de \$DOMAIN doit pointer vers cette machine."
