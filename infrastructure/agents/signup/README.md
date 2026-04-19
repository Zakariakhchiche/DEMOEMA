# DEMOEMA Manual Actions Agent (ex "Signup Automator")

Container isolé VPS qui automatise **toutes les actions manuelles** dont l'agent-platform a besoin pendant ses développements :

1. **Signups API** (scope initial) — création comptes sur portails publics FR gratuits pour débloquer sources auth
2. **DNS panel IONOS** — ajouter enregistrements A/MX/TXT/CNAME sans se connecter manuellement
3. **Forms corporate** — tout portail web avec form simple (non-2FA, non-CAPTCHA)
4. **GitHub UI** (à implémenter) — opérations PR/merge/resolve-conflicts pas faisables en CLI

Chaque "action manuelle" = 1 fichier Python dans `signup_agent/flows/<action>.py`, orchestré par `main.py` via `sources_to_signup` (ou `actions_to_run` — même mécanique).

## Isolation sécuritaire (non négociable)

- Container Docker **read-only**, `cap_drop: ALL`, `no-new-privileges`
- Network isolé (`signup-net`, pas de shared-supabase)
- Volumes minimaux : `profile.yaml:ro`, `.env.signups:rw`, `audit:rw`
- User non-root (`pwuser` de l'image Playwright)
- **Aucun accès** : Gmail perso, banking, filesystem host, secrets des autres services
- Audit trail complet (screenshots par étape, chiffrés pour le password)

## Flows disponibles

| Flow | Type | Statut | Note |
|---|---|---|---|
| `insee_sirene` | signup | ✅ MVP | Priorité 1, form simple |
| `dns_ionos` | DNS panel | ✅ MVP | Ajout records A/MX/TXT/CNAME, STOP si 2FA |
| `piste_gouv` | signup | ✅ MVP | Judilibre + Légifrance (OAuth2 client_credentials) |
| `france_travail` | signup | ✅ MVP | API Offres d'emploi v2, ROME 4.0 |
| `inpi_rne` | signup | À implémenter | Priorité 2 |
| `epo_ops` | signup | À implémenter | Brevets européens |
| `github_ui` | ops | À implémenter | Merge PR, resolve conflicts (ToS OK si compte propre) |
| Companies House UK | signup | ❌ Manual | reCAPTCHA + vérif postale |

## Setup initial (1 fois, ~15 min)

### 1. Email dédié projet (choisir Option C recommandée)

**Option A — ProtonMail free** (2 min)
- Créer `demoema@proton.me` sur https://proton.me
- Générer app password pour IMAP
- Renseigner dans `profile.yaml` : `project_email`, `project_email_imap_host=imap.proton.me`, `project_email_user`, + password dans `.env.signups`

**Option B — SimpleLogin alias → forward vers ta boîte** (1 min)
- https://simplelogin.io, créer alias `demoema-signups.xyz@slmail.me`
- L'agent ne peut PAS lire — tu copies manuellement les liens de vérif
- Mode "semi-auto"

**Option C — Postfix VPS** (30 min setup, 100% isolé, recommandée)
- Script clé en main : `setup-postfix.sh` (Postfix + Dovecot + OpenDKIM)
- Boîte `signups@demoema.fr` lisible depuis container via `imap://127.0.0.1:143`
- Setup (sur VPS, en root) :
  ```bash
  export MAIL_PASSWORD=$(openssl rand -base64 24)
  echo "Password généré (à garder) : $MAIL_PASSWORD"
  bash /root/DEMOEMA/infrastructure/agents/signup/setup-postfix.sh
  ```
- **DNS IONOS requis** (à faire AVANT) :
  - `A  mail.demoema.fr → 82.165.242.205`
  - `MX demoema.fr priorité 10 → mail.demoema.fr`
  - `TXT demoema.fr : v=spf1 ip4:82.165.242.205 -all`
  - `TXT mail._domainkey.demoema.fr : <DKIM publique générée par opendkim-genkey>`
  - `PTR 82.165.242.205 → mail.demoema.fr` (ticket support IONOS)
- Après setup : exporter `POSTFIX_IMAP_PASSWORD=$MAIL_PASSWORD` dans `.env.signups`

### 2. Compléter profile.yaml

```bash
cp profile.yaml.example profile.yaml
nano profile.yaml  # remplir company_name, contact_*, project_email
```

### 3. Init .env.signups vide

```bash
touch .env.signups && chmod 600 .env.signups
```

### 4. Build + run

```bash
docker compose -f docker-compose.signup.yml build
docker compose -f docker-compose.signup.yml run --rm signup-agent
```

## Comportement en cas d'échec partiel

| Cas | Action agent | Action toi |
|---|---|---|
| CAPTCHA détecté | Screenshot + stop + notif Slack | Clic manuel dans form (session partagée OU recommencer sans automation) |
| CGU checkbox required | STOP (ne coche JAMAIS auto) | Cocher CGU + submit manuellement |
| Email verification non reçu 15min | STOP + notif | Vérifier boîte mail, transférer lien à agent |
| 2FA / SMS required | STOP | Fallback manuel complet |
| Form inconnu (UI changée) | Screenshot + stop | Update flow Python ou fallback manuel |

## Audit trail

Après chaque run, structure dans `audit/<source>/<timestamp>/` :
- Screenshots étape par étape
- `password.txt` (chmod 600, pour login manuel si besoin continuer)
- `summary.json` (timestamps + status par étape)

Les credentials extraits sont écrits dans `.env.signups` (jamais en clair dans audit).

## Intégration au pipeline DEMOEMA

Une fois creds obtenus dans `.env.signups`, à appliquer au container principal :

```bash
# Merge .env.signups dans .env principal
cat .env.signups >> /root/DEMOEMA-agents/.env
# Restart agents-platform pour prendre en compte
docker compose -f /root/DEMOEMA-agents/docker-compose.agents.yml restart agents-platform
# Déclencher ingestion des sources débloquées
curl -X POST -H "X-API-Key: $KEY" http://127.0.0.1:8100/ingestion/run/insee_sirene_v3
```

## Limites connues

- **Sélecteurs CSS hardcodés** par flow : si INSEE/INPI/etc. refont leur UI, le flow casse. Le maintainer cron peut detecter (screenshots `99_*` dans audit) et notifier.
- **Pas de CAPTCHA bypass** : le flow STOP et escalade. Pas de tentative contourner (ToS + ethical).
- **Single-shot par source** : chaque source signup-ée 1 fois. Idempotence via check `.env.signups` avant lancement.

## Pas déployé tant que

- [ ] Email dédié projet configuré (Option A/B/C au choix)
- [ ] `profile.yaml` rempli avec infos corporate projet (pas données perso)
- [ ] Founder a validé le flow sur 1 source test avant batch
