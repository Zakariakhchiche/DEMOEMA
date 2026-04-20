#!/usr/bin/env bash
# DEMOEMA — Setup Postfix + Dovecot VPS pour email dédié signups@demoema.fr (Option C)
# Exécuté par root sur le VPS. Idempotent.
#
# Prérequis DNS (à faire avant côté IONOS panel) :
#   - A record        mail.demoema.fr → 82.165.242.205
#   - MX record       demoema.fr priorité 10 → mail.demoema.fr
#   - PTR record      82.165.242.205 → mail.demoema.fr (reverse DNS, contacter IONOS support)
#   - TXT record SPF  demoema.fr → "v=spf1 ip4:82.165.242.205 -all"
#   - TXT record DKIM (setup via opendkim ci-dessous)
#
# Après run, boîte signups@demoema.fr accessible en IMAP local (127.0.0.1:143)
# depuis le container demomea-signup-agent.

set -euo pipefail

DOMAIN="${DOMAIN:-demoema.fr}"
MAIL_HOST="mail.${DOMAIN}"
MAIL_USER="signups"
MAIL_PASSWORD="${MAIL_PASSWORD:-}"  # doit être fourni via env var

if [[ -z "$MAIL_PASSWORD" ]]; then
  echo "ERREUR: MAIL_PASSWORD env var manquante. Génère-le : openssl rand -base64 24"
  exit 1
fi

echo "==> Install Postfix + Dovecot + OpenDKIM"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
# Pré-config postfix en "Internet Site" non-interactif
debconf-set-selections <<< "postfix postfix/main_mailer_type string 'Internet Site'"
debconf-set-selections <<< "postfix postfix/mailname string '$DOMAIN'"
apt-get install -y postfix dovecot-core dovecot-imapd opendkim opendkim-tools mailutils

echo "==> Create user for mail"
id -u mail-demoema >/dev/null 2>&1 || useradd -m -r mail-demoema -s /bin/false

echo "==> Postfix main.cf"
cat > /etc/postfix/main.cf <<EOF
myhostname = $MAIL_HOST
mydomain = $DOMAIN
myorigin = \$mydomain
inet_interfaces = all
inet_protocols = ipv4
mydestination = localhost, $DOMAIN, $MAIL_HOST
home_mailbox = Maildir/
mynetworks = 127.0.0.0/8 [::1]/128 172.16.0.0/12 192.168.0.0/16
smtpd_banner = \$myhostname ESMTP

# TLS (Let's Encrypt via Caddy ACME peut générer)
smtpd_tls_cert_file = /etc/ssl/certs/ssl-cert-snakeoil.pem
smtpd_tls_key_file = /etc/ssl/private/ssl-cert-snakeoil.key
smtpd_use_tls = yes

# Accept mail from anywhere (we receive verification emails)
smtpd_recipient_restrictions = permit_mynetworks, reject_unauth_destination

# DKIM via opendkim
milter_default_action = accept
milter_protocol = 6
smtpd_milters = inet:localhost:8891
non_smtpd_milters = inet:localhost:8891

# Limits
message_size_limit = 10485760  # 10 MB
mailbox_size_limit = 1073741824  # 1 GB
EOF

echo "==> Dovecot conf (IMAP local-only)"
cat > /etc/dovecot/dovecot.conf <<'EOF'
protocols = imap
listen = 127.0.0.1

mail_location = maildir:~/Maildir

passdb {
  driver = passwd-file
  args = /etc/dovecot/users
}
userdb {
  driver = passwd-file
  args = /etc/dovecot/users
}

auth_mechanisms = plain login

ssl = no  # IMAP local only via 127.0.0.1
disable_plaintext_auth = no

service imap-login {
  inet_listener imap {
    address = 127.0.0.1
    port = 143
  }
}

log_path = /var/log/dovecot.log
info_log_path = /var/log/dovecot-info.log
EOF

echo "==> Créer utilisateur mail $MAIL_USER@$DOMAIN"
install -d -m 0755 -o mail-demoema -g mail-demoema /home/mail-demoema/Maildir
install -d -m 0700 -o mail-demoema -g mail-demoema /home/mail-demoema/Maildir/cur /home/mail-demoema/Maildir/new /home/mail-demoema/Maildir/tmp

# Dovecot passwd-file format: user:{scheme}hash:uid:gid::home::
HASH=$(doveadm pw -s SHA512-CRYPT -p "$MAIL_PASSWORD")
UID_M=$(id -u mail-demoema)
GID_M=$(id -g mail-demoema)
echo "${MAIL_USER}@${DOMAIN}:${HASH}:${UID_M}:${GID_M}::/home/mail-demoema::" > /etc/dovecot/users
chmod 640 /etc/dovecot/users
chown root:dovecot /etc/dovecot/users

echo "==> Postfix virtual alias (signups@demoema.fr → mail-demoema Maildir)"
cat > /etc/postfix/virtual <<EOF
${MAIL_USER}@${DOMAIN}  mail-demoema
EOF
postmap /etc/postfix/virtual
echo "virtual_alias_maps = hash:/etc/postfix/virtual" >> /etc/postfix/main.cf

echo "==> Setup DKIM"
install -d -o opendkim -g opendkim /etc/opendkim/keys/$DOMAIN
cd /etc/opendkim/keys/$DOMAIN
opendkim-genkey -s mail -d $DOMAIN
chown opendkim:opendkim mail.private
DKIM_TXT=$(cat mail.txt)
echo "==> Ajoute ce TXT record DNS (mail._domainkey.${DOMAIN}) :"
echo "$DKIM_TXT"

cat > /etc/opendkim.conf <<EOF
Syslog yes
UMask 002
Mode sv
SubDomains yes
AutoRestart yes
AutoRestartRate 10/1h
Background yes
DNSTimeout 5
SignatureAlgorithm rsa-sha256

KeyFile /etc/opendkim/keys/$DOMAIN/mail.private
Selector mail
Domain $DOMAIN

Socket inet:8891@localhost
EOF

systemctl restart opendkim postfix dovecot
systemctl enable opendkim postfix dovecot

echo "==> Firewall ports (UFW)"
ufw allow 25/tcp 2>/dev/null || true   # SMTP entrant pour recevoir
ufw allow 143/tcp 2>/dev/null || true  # IMAP (restreint 127.0.0.1 côté dovecot)

echo "==> Test local"
echo "Subject: test local" | sendmail -v ${MAIL_USER}@${DOMAIN} || true
sleep 2
ls -la /home/mail-demoema/Maildir/new/ || echo "(pas encore de mail)"

echo ""
echo "==> SETUP TERMINÉ"
echo "Boîte mail : ${MAIL_USER}@${DOMAIN}"
echo "IMAP local : 127.0.0.1:143 user=${MAIL_USER}@${DOMAIN}"
echo "Password : stocké uniquement dans ce shell — ajouter à .env.signups :"
echo "  POSTFIX_IMAP_PASSWORD=\$MAIL_PASSWORD"
echo ""
echo "TODO DNS côté IONOS :"
echo "  1. A record        mail.${DOMAIN} → 82.165.242.205"
echo "  2. MX record       ${DOMAIN} priority 10 → mail.${DOMAIN}"
echo "  3. TXT SPF         ${DOMAIN} : 'v=spf1 ip4:82.165.242.205 -all'"
echo "  4. TXT DKIM        mail._domainkey.${DOMAIN} : (voir output opendkim-genkey ci-dessus)"
echo "  5. PTR reverse     82.165.242.205 → mail.${DOMAIN} (support IONOS)"
echo ""
echo "Test externe : envoie un email à ${MAIL_USER}@${DOMAIN} depuis Gmail, attends 30s, puis :"
echo "  ls -la /home/mail-demoema/Maildir/new/"
