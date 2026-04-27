# Migration VPS — Runbook

Procédure complète pour migrer un VPS DEMOEMA vers un nouveau host (cas IONOS,
Hetzner ou autre). Les scripts associés sont dans `infrastructure/scripts/`.

## Pré-requis

- Accès root au **VPS source** (= ancien, prod actuelle) via clé SSH dédiée
  (`~/.ssh/demoema_ionos_ed25519`)
- Accès root au **VPS target** (= nouveau) via mot de passe initial OU clé SSH
- Tes clés DEMOEMA disponibles localement
- Ton machine locale = **relay** : les pipes SSH transitent via toi mais ne
  laissent rien sur ton disque ni dans le transcript

## Phase 0 — Provisioning du nouveau VPS

### 0a. Setup SSH (depuis ta machine locale)

Si le VPS target n'a pas encore ta clé deploy :

```bash
# Option A : panel IONOS / Hetzner → ajouter la pubkey dans Server SSH Keys
cat ~/.ssh/demoema_ionos_ed25519.pub
# colle dans le panel

# Option B : si tu as un mot de passe root initial, push la clé via paramiko
VPS_PWD='...' python <<'PY'
import paramiko, os
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("NEW_HOST", username="root",
               password=os.environ['VPS_PWD'],
               allow_agent=False, look_for_keys=False)
with open(os.path.expanduser("~/.ssh/demoema_ionos_ed25519.pub")) as f:
    pub = f.read().strip()
client.exec_command(
    f"mkdir -p ~/.ssh && chmod 700 ~/.ssh && "
    f"echo {pub!r} >> ~/.ssh/authorized_keys && "
    f"sort -u ~/.ssh/authorized_keys -o ~/.ssh/authorized_keys && "
    f"chmod 600 ~/.ssh/authorized_keys"
)
client.close()
PY
```

### 0b. Inventaire & install deps

```bash
ssh -i ~/.ssh/demoema_ionos_ed25519 root@NEW_HOST '
    set -e
    # Inventaire
    hostname; uptime; nproc; free -h; df -h /; cat /etc/os-release | head -3
    # Install deps si absentes
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq curl git ufw ca-certificates
    if ! command -v docker >/dev/null; then
        curl -fsSL https://get.docker.com | sh
    fi
    docker --version && docker compose version && git --version
    # Firewall : 22/80/443 only (audit SE-13 : pas exposer 7474/7687 Neo4j)
    ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp
    ufw --force enable
'
```

### 0c. Clone repo + bootstrap

```bash
ssh -i ~/.ssh/demoema_ionos_ed25519 root@NEW_HOST '
    cd /root && git clone https://github.com/Zakariakhchiche/DEMOEMA.git
    cd DEMOEMA
    chmod +x infrastructure/scripts/bootstrap-vps.sh
    bash infrastructure/scripts/bootstrap-vps.sh
'
```

À ce stade :
- `.env` généré avec passwords aléatoires
- Stack principale (backend + frontend + caddy) up
- Stack agents (datalake-db + agents-platform) up
- Schémas Postgres `audit` + `silver` + `bronze` créés (vides)
- Crons backup + healthz monitor installés

## Phase 1 — Migration des secrets (.env)

Le `.env` source contient les API keys (OLLAMA, DEEPSEEK, INPI, SUPABASE, ...)
+ les passwords postgres prod. On le copie via pipe SSH (jamais sur disque
local, jamais dans le transcript).

```bash
./infrastructure/scripts/migrate-vps.sh \
    --source root@OLD_HOST \
    --target root@NEW_HOST \
    --phase env
```

## Phase 2 — Migration de la donnée Postgres

`pg_dump` source → `pg_restore` target via pipe SSH chiffré. Le target a
déjà des passwords aléatoires baked in (de bootstrap-vps.sh) — le script
fait un `ALTER USER` automatique pour matcher les passwords source avant
le restore.

```bash
./infrastructure/scripts/migrate-vps.sh \
    --source root@OLD_HOST \
    --target root@NEW_HOST \
    --phase datalake
```

Durée typique : **30-90 min** selon volume (datalake DEMOEMA ≈ 70-200 GB
selon ingestions bronze). Le pipe SSH transite via ta machine locale —
prévoir une connexion stable.

À la fin, le script :
1. Restart agents-platform pour reconnecter à la DSN
2. Vérifie `count(*) FROM pg_matviews WHERE schemaname='silver'` doit matcher source
3. Affiche le `/healthz`

## Phase 2 bis — Bronze full backfill (premier launch agents)

### Mécanisme natif

**La majorité des fetchers gèrent leur premier-run automatiquement.** La
convention DEMOEMA (cf. `sources/bodacc.py:147-164`) :

```python
async def fetch_<sid>_delta() -> dict:
    # Check if table is empty → première ingestion = backfill
    if existing == 0:
        window = timedelta(days=BACKFILL_DAYS_FIRST_RUN)  # 10 ans par défaut
    else:
        window = timedelta(hours=INCREMENTAL_HOURS)        # 48h delta normal
    ...
```

Au premier tick scheduler après la migration, chaque fetcher détecte sa
bronze table vide et bascule sur la fenêtre élargie. Bronze se remplit
progressivement (BODACC seul = 30M+ rows en ~60-120 min).

**Coverage** : 57 / 71 fetchers (80%) ont ce pattern. Les 6 fetchers RSS
(google news, cfnews, la_tribune, les_echos, press, usine_nouvelle) sont
exclus légitimement (un flux RSS = derniers articles only, pas de
backfill possible).

### Trous connus à patcher (audit 2026-04-27)

5 fetchers n'ont pas le pattern first-run et resteraient vides après
migration :

- `inpi_comptes_annuels.py` — INPI dépôts comptes (~1.5M/an)
- `insee_sirene_v3.py` — SIRENE 40M établissements
- `opensanctions.py` — flux sanctions
- `osint_companies.py` — base OSINT
- `press_articles.py` — articles presse

Ces 5 sont listés dans `tests/test_first_run_coverage.py:TODO_NEED_FIRST_RUN_PATCH`.
Le test garantit qu'aucun NOUVEAU fetcher ne sera ajouté sans le pattern.

**Workaround migration** : pour ces 5 sources, déclencher manuellement
`/api/admin/run-all` après la migration datalake (avec `CRON_SECRET` en
header), OU laisser le `silver_maintainer` regen via codegen LLM (cycle
30 min) qui va régénérer le fetcher avec le prompt actualisé qui inclut
la règle #6 ("Backfill first-run", cf. `codegen.py:130`).

### Vérification post-launch

Après 6-24h sur le nouveau VPS, count les bronze tables :

```bash
ssh root@NEW_HOST 'docker exec demomea-datalake-db psql -U postgres -d datalake -c "
    SELECT n.nspname || \".\" || c.relname AS table_name, c.reltuples::bigint AS approx_rows
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = '\''bronze'\'' AND c.relkind = '\''r'\''
    ORDER BY c.reltuples DESC LIMIT 30
"'
```

Si une table est restée à 0 après plusieurs ticks attendus, vérifier
ses logs : `docker logs demomea-agents-platform | grep <source_id>`.

## Phase 3 — Migration Neo4j (optionnel)

Le rebuild Neo4j est quotidien automatique (job APScheduler 04:00 Paris,
`neo4j_sync.run_neo4j_rebuild`). Plutôt que de transférer le volume, on
**laisse le job nightly recréer le graphe à partir du Postgres restauré**.

Si urgent (rebuild immédiat) :

```bash
ssh -i ~/.ssh/demoema_ionos_ed25519 root@NEW_HOST '
    docker exec demomea-agents-platform python -c "
        import asyncio
        from ingestion.neo4j_sync import run_neo4j_rebuild
        print(asyncio.run(run_neo4j_rebuild()))
    "
'
```

## Phase 4 — DNS switch

Repointer les A records `demoema.fr`, `www.demoema.fr`, `api.demoema.fr` vers
l'IP du nouveau VPS. Caddy (déjà up sur le nouveau) générera les certificats
Let's Encrypt automatiquement.

```bash
# Vérifier que Caddy peut atteindre :80 et :443 (UFW déjà ouvert)
ssh -i ~/.ssh/demoema_ionos_ed25519 root@NEW_HOST '
    docker logs demomea-caddy --tail 30
'
```

Le TTL DNS de IONOS est typiquement 1-4h — propagation progressive.

## Phase 5 — Validation comparative (avant decom de l'ancien)

L'ancien VPS reste **live** pendant la phase de validation. Compare les
endpoints publics + les counts DB :

```bash
# Côté DB
ssh root@OLD_HOST 'docker exec demomea-datalake-db psql -U postgres -d datalake -tAc "SELECT count(*) FROM pg_matviews WHERE schemaname='\''silver'\''"'
ssh root@NEW_HOST 'docker exec demomea-datalake-db psql -U postgres -d datalake -tAc "SELECT count(*) FROM pg_matviews WHERE schemaname='\''silver'\''"'
# Doivent matcher

# Côté API
ssh root@OLD_HOST 'docker exec demomea-agents-platform curl -sf http://localhost:8100/healthz'
ssh root@NEW_HOST 'docker exec demomea-agents-platform curl -sf http://localhost:8100/healthz'
```

## Phase 6 — Désactivation de l'ancien VPS

**SEULEMENT après validation OK + DNS propagé + 24-48h d'observation.**

```bash
# Stop tous les services sur l'ancien VPS
ssh root@OLD_HOST '
    cd /root/DEMOEMA
    docker compose -f infrastructure/agents/docker-compose.agents.yml down
    docker compose down
'
# Cancel chez IONOS le serveur ancien
```

## Troubleshooting connu

### `network shared-supabase declared as external, but could not be found`

Cette stack principale référence un network external nommé `shared-supabase`
(legacy : Supabase self-hosted utilisait ce nom). Le bootstrap-vps.sh récent
le crée automatiquement. Si tu vois cette erreur :

```bash
docker network create shared-supabase
```

### `Permission denied (publickey,password)` au premier SSH

Ta clé n'est pas encore dans `~/.ssh/authorized_keys` du target. Voir 0a.

### Postgres auth fail après pg_restore

Le password dans `.env` du target ne matche pas pg_authid restauré. Le
`migrate-vps.sh phase=datalake` fait un ALTER USER avant restore — vérifie
que cette étape n'a pas échoué silencieusement.

### `chmod +x` perdu après git clone

Sur certains hosts (Windows en clone source), `infrastructure/scripts/*.sh`
perd le bit exécutable :

```bash
chmod +x infrastructure/scripts/*.sh
```
