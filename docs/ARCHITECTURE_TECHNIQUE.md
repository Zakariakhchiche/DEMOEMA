# ARCHITECTURE TECHNIQUE — V4.2 (VPS IONOS partiellement déployé)

> ✅ **V4.2 — Migration applicative exécutée le 2026-04-20** sur VPS IONOS `82.165.242.205` (Debian 13, 12 vCPU, 24 GiB RAM, 709 GB).
>
> ⚠️ **Note d'honnêteté** : le déploiement réalisé est **plus simple** que la cible V4.1 "Postgres nu + Dagster + dbt + Ollama dual-agent". Le founder a retenu **Supabase self-hosted + Caddy + 3 containers DEMOEMA** : gain de temps, stack éprouvée, migration cloud→self-hosted directe. Les composants Ollama, Dagster, dbt, Redis dédié, MinIO, monitoring **restent à ajouter** (roadmap Q3 2026 post Lead Data Eng).
>
> | Couche | V4.0 (avant) | **V4.2 (réel 2026-04-20)** | Statut |
> |---|---|---|---|
> | Frontend | Next.js 15 sur Vercel | Container Docker `demomea-frontend` (Next.js 15, expose :3000 interne) | ✅ PROD |
> | Backend | FastAPI serverless Vercel | Container Docker `demomea-backend` (FastAPI, expose :8000 interne) | ✅ PROD |
> | Database | Supabase Cloud (AWS) | **Supabase self-hosted** (container `supabase-db` = Postgres 15 + pgvector + pg_trgm natifs) | ✅ PROD |
> | Auth | Supabase Auth (AWS) | **Supabase Auth (GoTrue)** self-hosted dans le même stack | ✅ PROD |
> | Storage objet | ❌ | **Supabase Storage** self-hosted (API compatible S3) | ✅ PROD |
> | Reverse proxy | Vercel edge | **Caddy 2.8** (container `demomea-caddy`) avec ACME automatique (pas de certbot cron) | ✅ PROD |
> | LLM user-facing | Claude API SSE | Claude API SSE (inchangé) | ✅ PROD |
> | CI/CD | Vercel auto-deploy | `/root/DEMOEMA/deploy.sh` (`git pull && docker compose up -d --build`) — workflow GitHub Actions présent localement mais non activé | 🔧 Partiel |
> | Cache Redis | ❌ | ❌ **non déployé** | ❌ SCRUM-76 à faire |
> | Orchestration (Dagster) | Vercel Cron | ❌ **non déployé** | ❌ Q3 2026 |
> | Transformation (dbt) | Python inline | ❌ **non déployé** | ❌ Q3 2026 |
> | LLM ingestion (Ollama dual-agent) | ❌ | ❌ **non déployé** | ❌ Q3 2026 (Epic SCRUM-80 à démarrer) |
> | Monitoring (Prometheus/Loki/Grafana) | Vercel Analytics | ❌ **non déployé** | ❌ SCRUM-78 prioritaire |
> | Backups | Supabase auto | ❌ **non configuré** | ❌ **SCRUM-91 URGENT** |
> | TLS | Vercel | Caddy ACME auto (Let's Encrypt) | ✅ PROD |
>
> **Containers actifs** (2026-04-20 03:00 UTC) : 3 DEMOEMA (`demomea-caddy`, `demomea-backend`, `demomea-frontend`) + 15 Supabase (`supabase-db/-auth/-studio/-storage/-kong/-realtime/-pooler/-rest/-meta/-analytics/-vector/-imgproxy/-edge-functions`).
>
> **Coût VPS réel** : ~65-80 €/mois (12 vCPU/24 GB IONOS Paris).
>
> Source ground truth : [`ETAT_REEL_2026-04-20.md`](./ETAT_REEL_2026-04-20.md).
> Runbook : [`DEPLOYMENT_RUNBOOK.md`](./DEPLOYMENT_RUNBOOK.md).
> Configs réelles snapshots : [`../infrastructure/vps-current/`](../infrastructure/vps-current/).
> Artefacts target V4.3 non déployés : [`../infrastructure/`](../infrastructure/) racine.
> Décisions : [`DECISIONS_VALIDEES.md`](./DECISIONS_VALIDEES.md) §9.
> Epics Jira : SCRUM-66 (migration, **7/12 Done**) · SCRUM-80 (agents, **0/10 démarré**).
>
> Source ground truth : [`ETAT_REEL_2026-04-19.md`](./ETAT_REEL_2026-04-19.md).
> Décision verrouillée : [`DECISIONS_VALIDEES.md`](./DECISIONS_VALIDEES.md) §9.
> Tracking : ticket Jira SCRUM-65 (Done) + Epic migration SCRUM-66.
>
> ⚠️ **Document V2 — voir bannière ci-dessous pour les corrections post-audit 2026-04-17.**
>
> Source unique de vérité chiffrée : [`FINANCES_UNIFIE.md`](./FINANCES_UNIFIE.md)
> Décisions verrouillées : [`DECISIONS_VALIDEES.md`](./DECISIONS_VALIDEES.md)
> Plan opérationnel : [`PLAN_DEMARRAGE_Q2-Q4_2026.md`](./PLAN_DEMARRAGE_Q2-Q4_2026.md)
>
> ⚠️ **Calendrier** : "Y1 2026" démarre **en avril 2026** (pas janvier). Setup infra : juillet 2026 (post-pré-amorçage).
> ⚠️ **AI Act** : pas de fine-tuning Mistral (Claude/Mistral via API uniquement). CGU clause "no automated decision". Cf. `AI_ACT_COMPLIANCE.md`.
> ⚠️ **Sources** : INPI RBE retiré (CJUE), Trustpilot/Google Reviews retirés (CGU).
>
> Datalake et plateforme pour héberger 5M+ entreprises FR. **Approche progressive** : start simple Y1 (Postgres + DuckDB), ajouter composants seulement quand nécessaire.
>
> **Principe directeur** : ne pas sur-ingéniérer. Ne pas adopter ClickHouse/Neo4j/Qdrant tant qu'on n'en a pas besoin.

---

## Évolution de la stack par année

| Composant | Y1 (2026) | Y2 (2027) | Y3 (2028) | Y4 (2029) |
|---|---|---|---|---|
| **OLTP** | Postgres 16 | Postgres 16 | Postgres + replicas | Postgres clustered |
| **OLAP** | DuckDB local + Postgres | DuckDB + Postgres | **+ ClickHouse** (>50M lignes) | ClickHouse cluster |
| **Storage** | S3 Scaleway + Parquet | + Iceberg | Iceberg + lifecycle | Iceberg multi-region |
| **Orchestration** | **Dagster (light)** | Dagster | Dagster + clustering | Dagster + Kubernetes |
| **Transformation** | dbt-core | dbt-core | dbt-core | dbt + dbt Cloud |
| **Graphe** | ❌ Tables Postgres | ❌ Tables Postgres | **+ Neo4j Community** | Neo4j Enterprise |
| **Vector DB** | ❌ pgvector | ❌ pgvector | **+ Qdrant** | Qdrant cluster |
| **Cache** | Redis | Redis | Redis cluster | Redis cluster |
| **Search** | Postgres FTS | Postgres FTS | + Meilisearch ou ES | Elasticsearch |
| **API** | FastAPI | FastAPI + GraphQL | FastAPI + GraphQL | + gRPC interne |
| **Front** | Next.js 14 | Next.js 14 | Next.js 14 | Next.js 14 |
| **LLM** | Claude API | Claude + Mistral | + fine-tuning | Multi-LLM routing |
| **Auth** | Supabase Auth | Clerk ou Supabase | Clerk | Clerk + SSO |
| **Hosting** | Scaleway + Vercel | Scaleway + Vercel | + UE Frankfurt | Multi-région |
| **Monitoring** | Grafana Cloud | + Datadog (option) | Datadog full | Datadog enterprise |

---

## Stack Y1 — minimaliste mais robuste

```
┌────────────────────────────────────────────────────┐
│  SOURCES (top 30 sources prioritaires Y1)          │
└──────────┬─────────────────────────────────────────┘
           │
┌──────────▼──────────┐
│  INGESTION          │  Dagster (1 instance) + httpx
│  - APIs : httpx     │  Bulk : DuckDB (lecture Parquet directe)
│  - RSS : feedparser │  Scheduler : daily / weekly / monthly
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  RAW (S3 Scaleway)  │  Parquet partitionné /source/date
│  + dbt staging      │  Bronze → Silver → Gold via dbt
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  POSTGRES 16        │  ⭐ Source unique de vérité Y1
│  + pgvector         │  - 5M entreprises tables
│  + pg_trgm (search) │  - 15M personnes
│  + JSONB            │  - 30M mandats
│                     │  - pgvector pour embeddings light
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  FastAPI + Redis    │  API REST simple
│  + auth Supabase    │  Cache via Redis
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Next.js 14 (Vercel)│  Front + landing + dashboard
└─────────────────────┘
```

**Pourquoi Postgres seul Y1 ?**
- 5M lignes × 200 colonnes = **30 GB** = parfaitement gérable par Postgres
- Postgres + pgvector + pg_trgm = couvre 90% des besoins (lookup, search, embeddings)
- Coût infra ~200€/mois vs 1500€/mois pour ClickHouse + Neo4j + Qdrant
- **1 seul système à maintenir** (vs 4) — critique avec 1 devops part-time
- Migration ClickHouse/Neo4j possible Y2 si la perf devient un problème

**Quand basculer ?**
- ClickHouse : quand requêtes analytiques > 5s sur Postgres OU >50M lignes événements
- Neo4j : quand requêtes graphe profondes (3+ degrés) deviennent fréquentes
- Qdrant : quand pgvector ne suit plus (>10M embeddings)

---

## Choix techniques justifiés (V2)

| Layer | Choix Y1 | Pourquoi (et pas autre chose) |
|---|---|---|
| **Storage froid** | Parquet sur S3 Scaleway | Souveraineté FR, ZSTD, lecture DuckDB directe |
| **OLTP + OLAP léger** | Postgres 16 + extensions | 5M lignes = pas besoin d'OLAP dédié. Pgvector + pg_trgm + JSONB suffit |
| **Dev local** | DuckDB | Bosser sur snapshots Parquet en local sans cluster |
| **Orchestration** | Dagster OSS (1 nœud) | Asset-centric, lineage natif, simple à démarrer |
| **Transformation** | dbt-core OSS | Standard, tests intégrés, doc auto |
| **Search** | Postgres FTS + pg_trgm | Fonctionne pour 5M entreprises, pas besoin d'ES Y1 |
| **Embeddings** | pgvector | Cohabite avec Postgres, pas un système séparé |
| **Cache** | Redis (Scaleway managed) | Simple, éprouvé |
| **API** | FastAPI | Garder l'existant Python |
| **Front** | Next.js 14 | Garder l'existant |
| **Auth** | Supabase Auth (gratuit jusqu'à 50k users) | Plus simple que Clerk pour Y1, migration possible |
| **LLM** | Claude API uniquement Y1 | Mistral ajouté Y2 quand fine-tuning maîtrisé |
| **Monitoring** | Grafana Cloud (free tier) | Suffit Y1, Datadog payant en Y2-Y3 |
| **Erreurs** | Sentry | Standard |

---

## Modèle de données Postgres (Y1)

### Schéma core

```sql
-- ENTREPRISES (5M lignes)
CREATE TABLE entreprises (
  entity_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  siren            CHAR(9) UNIQUE NOT NULL,
  lei              VARCHAR(20),
  opencorp_id      VARCHAR,
  wikidata_qid     VARCHAR,

  -- Identité
  denomination     VARCHAR NOT NULL,
  sigle            VARCHAR,
  nom_commercial   VARCHAR,
  date_creation    DATE,

  -- Classification
  naf              CHAR(5),
  naf_libelle      VARCHAR,

  -- Localisation siège (BAN normalisée)
  siege_adresse    JSONB,
  siege_dept       CHAR(3),
  siege_geo        GEOMETRY(POINT, 4326),

  -- Taille
  effectif_tranche VARCHAR,
  ca_dernier       NUMERIC,
  ebitda_dernier   NUMERIC,

  -- Statut
  statut           VARCHAR CHECK (statut IN ('actif','cesse','procedure')),
  date_statut      DATE,

  -- Scoring
  score_ma         INT CHECK (score_ma BETWEEN 0 AND 100),
  score_defaillance INT CHECK (score_defaillance BETWEEN 0 AND 100),

  -- Métadonnées
  derniere_maj     TIMESTAMPTZ DEFAULT now(),
  sources          TEXT[]
);

CREATE INDEX idx_entreprises_siren ON entreprises(siren);
CREATE INDEX idx_entreprises_naf ON entreprises(naf);
CREATE INDEX idx_entreprises_statut ON entreprises(statut);
CREATE INDEX idx_entreprises_score_ma ON entreprises(score_ma DESC);
CREATE INDEX idx_entreprises_denomination_trgm ON entreprises USING gin (denomination gin_trgm_ops);
CREATE INDEX idx_entreprises_geo ON entreprises USING gist (siege_geo);
```

### Tables périphériques

```sql
etablissements      -- 31M lignes (par SIRET)
personnes           -- 15M lignes (dirigeants)
mandats             -- 30M lignes (jonction temporelle)
evenements          -- ~50M lignes Y1 (BODACC, presse light)
sanctions           -- 500k lignes
contrats_publics    -- 5M lignes
biens_immobiliers   -- 30M transactions DVF
embeddings_text     -- pgvector, ~5M vecteurs (descriptions entreprises)
```

### Volume estimé Y1 (Postgres)

- Tables core : ~80 GB
- Index : ~30 GB
- WAL + replicas : ~50 GB
- **Total** : ~160 GB → 1 nœud Postgres `Pro-XS` Scaleway suffit (~200€/mois)

---

## Pipeline d'ingestion (Dagster)

### Structure

```
dagster_project/
├── assets/
│   ├── insee/
│   │   ├── sirene_stock.py        # Bulk mensuel (Parquet)
│   │   ├── sirene_deltas.py       # Delta quotidien
│   │   └── etablissements.py
│   ├── inpi/
│   │   ├── rne.py                 # Représentants légaux
│   │   └── comptes_annuels.py     # Parsing PDF/XBRL
│   ├── bodacc/
│   ├── judilibre/
│   ├── opensanctions/
│   └── ...
├── jobs/
│   ├── daily_refresh.py
│   ├── weekly_full.py
│   └── monthly_bulk.py
├── resources/
│   ├── postgres.py
│   ├── s3.py
│   └── dbt.py
└── sensors/
    ├── new_bodacc.py              # Webhook → reprocess
    └── source_health.py
```

### Stratégie par fréquence

| Fréquence | Sources | Approche |
|---|---|---|
| **Quotidien (nuit)** | Sanctions, BODACC delta, France Travail, Judilibre | Dagster jobs scheduled |
| **Hebdo** | DECP, BOAMP, brevets | Dagster |
| **Mensuel** | INSEE Sirene Stock, ESANE, DVF, ADEME | Dagster + DuckDB pour parsing Parquet |
| **À la demande** | Comptes annuels (par SIREN) | Dagster ops + cache Redis |

---

## Résolution d'entités (V2 — pragmatique)

**Y1** : approche **simple basée règles** :
- Match exact SIREN ↔ LEI (via GLEIF)
- Match exact SIREN ↔ Wikidata QID (via Wikidata SPARQL)
- Pas encore de matching probabiliste (Splink) — overkill Y1

**Y2** : si problèmes de doublons identifiés, ajouter Splink.

---

## Couche IA / ML (V2 — par étape)

### Y1
- **Scoring M&A** : LightGBM sur 50 features (subset des 103 signaux)
- **Search** : Postgres FTS + pg_trgm (suffit Y1)
- **Pas de NLP custom** — utiliser Claude pour extraire événements (LLM-as-NER)

### Y2
- **Scoring M&A v2** : 200+ features, modèle fine-tuné
- **NLP CamemBERT** fine-tuné sur articles M&A
- **Embeddings** : pgvector pour similarity entreprises

### Y3
- **Recommandations** cibles via embeddings
- **Predictive exit-timing** modèle dédié
- **Copilot multi-agent** (Claude + Mistral routing)

---

## Sécurité & conformité (Y1)

| Aspect | Y1 (minimum viable) | Y2-Y3 (industrialisation) |
|---|---|---|
| Auth | Supabase Auth + MFA optionnel | Clerk + SSO + RBAC fin |
| Audit log | Postgres table simple | Logs immuables + S3 archive |
| Chiffrement | TLS 1.3 + Postgres SSL + S3 chiffré | + KMS rotation |
| Secrets | Doppler (gratuit jusqu'à 5 users) | Vault HashiCorp |
| Backups | pg_dump quotidien sur S3 | + PITR + multi-région |
| RGPD | DPO externe + workflow suppression manuel | DPO interne + workflow auto |
| Souveraineté | Scaleway Paris uniquement | + Frankfurt OVH backup |
| Certifications | (rien Y1) | SOC2 Type I (Y2) → Type II (Y3) → ISO 27001 (Y4) |

---

## Observabilité (Y1)

- **Logs** : stdout → Grafana Cloud (free tier)
- **Métriques** : Prometheus → Grafana
- **Erreurs** : Sentry
- **Data quality** : dbt tests basiques + Great Expectations Y2
- **Freshness** : Dagster asset checks
- **SLO Y1** : 99% (1h downtime/mois OK)

---

## Coût infra réaliste (V2)

| Composant | Y1 | Y2 | Y3 | Y4 |
|---|---|---|---|---|
| Storage S3 (Scaleway) | 30€/mois | 150€ | 500€ | 1500€ |
| Postgres managed | 200€/mois | 600€ | 2000€ | 5000€ |
| ClickHouse | — | — | 1500€ | 5000€ |
| Neo4j | — | — | 800€ | 3000€ |
| Qdrant | — | — | 500€ | 2000€ |
| Compute (Dagster + workers) | 100€/mois | 400€ | 1500€ | 4000€ |
| Redis | 30€/mois | 100€ | 500€ | 1500€ |
| LLM API (Claude) | 200€/mois | 1500€ | 8000€ | 25000€ |
| Front (Vercel) | 20€/mois | 100€ | 500€ | 1500€ |
| Auth (Supabase → Clerk) | 0€ | 100€ | 800€ | 3000€ |
| Monitoring (Grafana → Datadog) | 0€ | 200€ | 1000€ | 3000€ |
| Sentry | 30€/mois | 100€ | 300€ | 800€ |
| Outils data (dbt, etc.) | 0€ | 100€ | 500€ | 2000€ |
| **Total mensuel** | **~600€** | **~3500€** | **~18000€** | **~57000€** |
| **Total annuel** | **~7000€** | **~42k€** | **~216k€** | **~684k€** |

**Variation vs V1** : Y1 −40% (de 12k€ à 7k€), Y2-Y4 stables.

---

## Migration de l'existant (Vercel actuel → V2)

### Quoi faire avec demoema.vercel.app ?

| Composant actuel | Statut V2 | Action |
|---|---|---|
| Frontend Next.js | À conserver, refactoring progressif | Garder même repo, refactor par module |
| FastAPI backend | À refactorer (séparer ingestion d'API) | Extraire data layer dans nouveau repo `demoema-data` |
| Module `data_sources.py` | À supprimer | Remplacé par Dagster + dbt |
| Cache Redis | À conserver | OK |
| MCP servers | À évaluer cas par cas | Garder ceux qui marchent |
| Déploiement Vercel | Frontend uniquement Y1 | Backend → Scaleway |
| Utilisateurs actuels | À migrer | Notification + migration auto en Q2 2026 |

### Migration en 3 étapes

1. **Q1 2026** : nouveau backend `demoema-data` parallèle, ancien tourne toujours
2. **Q2 2026** : front pointe progressivement vers nouveau backend (feature flags)
3. **Q3 2026** : décommission ancien backend, archive code

---

## Décisions tranchées vs ouvertes

### ✅ Tranché
- Postgres seul Y1 (pas ClickHouse)
- Dagster OSS (pas Airflow)
- dbt-core OSS
- Scaleway hosting
- Claude pour LLM Y1

### ⏳ À trancher Q1 2026
- Supabase Auth vs Clerk (pricing dépend du nb users)
- Grafana Cloud vs Datadog (Datadog meilleur mais cher)
- Garder Vercel pour front ou migrer Scaleway aussi (perf vs souveraineté)
- pg_trgm suffit ou besoin Meilisearch dès Y1 ?

### 🔮 À évaluer Y2
- Migration Postgres → ClickHouse (selon volumes événements)
- Ajout Neo4j (selon usage graphe)
- Splink pour entity resolution (selon qualité matching)
