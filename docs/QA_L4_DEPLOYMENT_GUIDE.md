# Guide de déploiement QA L4 — Activation effective post-merge

Ce document liste **tout ce qui doit être configuré** côté GitHub Secrets, infra VPS, et runners CI pour que les workflows Sprint 1→5 produisent des métriques réelles et fassent grimper le QCS de **~22 actuel → 90 cible (L4 production payante)**.

> **Référence** : skill `~/.claude/skills/qa-audit/` v3.0.0 + plan adoption L4 12 semaines.
> **PR consolidée Sprint 1-5** : #132 (à merger).

---

## 1. GitHub Secrets requis (à créer dans Settings → Secrets and variables → Actions)

### 1.1 Soda Core data quality (workflow `qa-data-quality.yml`)

```
DEMOEMA_PG_HOST      = (host VPS Postgres)
DEMOEMA_PG_PORT      = 5432
DEMOEMA_PG_DB        = demoema
DEMOEMA_PG_USER_RO   = demoema_qa  (à créer côté VPS, RO uniquement)
DEMOEMA_PG_PASSWORD_RO = (mot de passe sécurisé 32+ chars)
QA_SLACK_WEBHOOK     = https://hooks.slack.com/services/...  (optionnel)
```

**Création utilisateur Postgres RO côté VPS** :
```sql
CREATE USER demoema_qa WITH PASSWORD '<password>' NOSUPERUSER NOCREATEDB NOCREATEROLE;
GRANT CONNECT ON DATABASE demoema TO demoema_qa;
GRANT USAGE ON SCHEMA silver, gold, audit, bronze TO demoema_qa;
GRANT SELECT ON ALL TABLES IN SCHEMA silver, gold, audit, bronze TO demoema_qa;
ALTER DEFAULT PRIVILEGES IN SCHEMA silver, gold, audit, bronze
  GRANT SELECT ON TABLES TO demoema_qa;
```

### 1.2 DeepEval LLM judge (Sprint 4, optionnel — payant)

```
OPENAI_API_KEY        = sk-...  (si OpenAI judge — payant)
ou
LOCAL_LLM_JUDGE_URL   = http://localhost:8001/v1  (si LLM local)
ou
DEEPEVAL_SKIP_EVAL    = 1  (skip eval, garde scaffolding only)
```

> ⚠️ **No paid actions sans approbation explicite Zak** (mémoire `feedback_no_paid_actions.md`). Par défaut → `DEEPEVAL_SKIP_EVAL=1`.

### 1.3 Schemathesis fuzz (Sprint 1, dim 5)

Schemathesis bloqué sur prod par sandbox (DDoS auto-induit). 2 options :

**Option A — Staging local** :
```bash
# Lancer staging Docker sur runner CI
docker compose -f docker-compose.test.yml up -d backend
schemathesis run http://localhost:8000/openapi.json \
  --max-examples=10 --workers=2 --include-method=GET
```

**Option B — Endpoint dédié rate-limité prod** :
- Créer `/api/qa/openapi-fuzz-target` rate-limité 1 req/sec
- Schemathesis avec `--rate-limit 1/s`

---

## 2. Runners GitHub Actions

| Workflow | Runner | Trigger | Durée estim |
|---|---|---|---|
| `qa-data-quality.yml` | ubuntu-latest | cron 06h UTC quotidien + PR sur `qa/soda/**` | 5-10 min |
| `qa-mutation-testing.yml` | ubuntu-latest | cron lundi 04h UTC + manuel | 30-60 min |
| `qa-security.yml` | ubuntu-latest | push main + PR + cron lundi 05h UTC | 5-10 min |
| `security-redteam.yml` (existant) | ubuntu-latest | cron lundi 03h UTC + manuel | 20-40 min |
| `qa-doctrine-sync.yml` (existant) | ubuntu-latest | PR touchant doctrine | < 1 min |

**Action minimum nécessaire** : aucune, les workflows sont déjà self-contained avec `actions/setup-python@v5`.

---

## 3. Étapes post-merge PR #132

### Étape 1 — Activer Soda Core (impact +5.6 pts QCS dim 8)

1. Créer secrets GitHub `DEMOEMA_PG_*` (cf. §1.1)
2. Créer user `demoema_qa` Postgres RO sur VPS
3. Trigger manuel : `gh workflow run qa-data-quality.yml`
4. Vérifier artifact `soda-scan-results.json` → 0 fail attendu sur 33 checks

### Étape 2 — Activer mutation testing (impact +8 pts QCS dim 4)

1. `gh workflow run qa-mutation-testing.yml`
2. Attendre 30-60 min (mutmut sur 5 modules critiques, runner Linux)
3. Vérifier artifact `mutation-score.txt` → cible ≥ 80 %
4. Si < 80 % → écrire tests pytest pour mutations survivantes

### Étape 3 — Activer Bandit SAST (impact intégré dans dim 6 sécurité)

1. Workflow `qa-security.yml` se déclenche automatiquement au merge
2. Aller dans **Security → Code scanning** sur GitHub
3. Vérifier 0 finding HIGH severity Bandit
4. Vérifier SBOM CycloneDX uploadé

### Étape 4 — Activer Playwright frontend (impact MASSIF sur dims 6/9/10/11/14)

```bash
cd frontend
pnpm install                         # installe @playwright/test 1.59
pnpm exec playwright install         # download browsers (~500MB)
PLAYWRIGHT_BASE_URL=https://82-165-57-191.sslip.io \
  pnpm test:e2e:clickables           # smoke 1 navigateur
```

**Cible** : 100 % des ~316 cliquables PASS sur chromium-desktop.

Une fois validé localement, ajouter workflow `qa-frontend-e2e.yml` (à créer Sprint 6) qui run `pnpm test:e2e:matrix` sur 8 projets.

### Étape 5 — Re-run audit complet via skill

```bash
# Depuis n'importe quelle session Claude Code dans /c/Users/zkhch/DEMOEMA
/qa-audit l4-final
```

Cible : QCS ≥ 90 + tous les 14 axes Playbook E GO.

---

## 4. Trajectoire QCS — comment passer 22 → 90

| Action | Δ QCS | Cumul | Effort |
|---|---|---|---|
| Merge PR #132 | 0 | 22 | 0h |
| Activer Soda CI + 33 checks PASS | +5.6 (dim 8 30→100) | 27.6 | 1h secrets |
| Activer mutmut CI + 80 % score | +8 (dim 4 0→80) | 35.6 | 1h trigger + analyse |
| Activer Bandit + 0 HIGH finding | +0.5 (dim 15) | 36 | 30min review |
| Activer Playwright + matrix 8 projets | +25 (dims 6, 9, 10, 11, 14) | 61 | 4h init + tests |
| Sprint 6 — Dashboard 15D | +5 | 66 | 8h dev |
| Coverage backend 29 % → 70 % | +4 (dim 1 + 2) | 70 | 5j tests écrits |
| Sprint 7 — TLA+ light state machine | +3 | 73 | 3j |
| DeepEval LLM judge actif | +5 (dim 7 fine) | 78 | 1j config + budget |
| Pact contracts frontend↔backend | +5 | 83 | 3j |
| A/B shadow + chaos engineering | +4 | 87 | 5j |
| Visual regression Storybook | +5 (dim 9 30→100) | 92 | 4j |

**Total effort estimé** : ~30 jours-homme (vs 8-10 estimé initialement).
**Cible date** : 2026-07-25 si 1.5 dev plein temps.

---

## 5. Checklist PR review #132 (avant merge)

- [x] 6 commits Sprint 1+1.5+1.6+1.7+2+3+4+5 cohérents
- [x] **361 tests pytest PASS** + 1 skipped DeepEval (attendu)
- [x] Aucune dépendance payante par défaut (DeepEval skip strategy)
- [x] Soda Core 33 checks YAML validés offline (20/20 tests)
- [x] Bandit config double `.bandit` + `[tool.bandit]` synchronisés (15/15 tests)
- [x] mutmut config CI Linux (issue #397 Windows documentée)
- [x] Playwright matrix 8 projets, scaffolding clickables
- [x] CI workflows : `qa-data-quality.yml`, `qa-mutation-testing.yml`, `qa-security.yml`
- [x] doc `QA_L4_PROGRESS.md` + `QA_L4_DEPLOYMENT_GUIDE.md`
- [x] Pas de fuite de secrets dans le repo
- [x] Pas de modification code prod hors Sprint 1.7 tests scoring/validators

---

## 6. Risques résiduels post-merge

| Risque | Mitigation |
|---|---|
| Schemathesis fuzz prod = DDoS | Sandbox bloque, run sur staging Docker uniquement |
| DeepEval coût OpenAI judge | Skip par défaut, override explicit Zak required |
| mutmut score < 80 % révèle tests faibles | Sprint 2 dédié + écrire tests pour mutations survivantes |
| Soda Core checks fail sur prod (faux positifs MV vide) | Ajuster seuils dans `qa/soda/checks/*.yml` itérativement |
| Playwright tests flaky cross-browser | `forbidOnly: true` + `retries: 1` déjà configurés |
| CI durée totale > 30 min | Paralléliser via `workers=4` Playwright + `pytest-xdist` |

---

## 7. Référence rapide commandes

```bash
# Audit local (skill v3.0.0)
/qa-audit smoke-deep        # 5-10 min : 10 questions M&A baseline
/qa-audit regression        # 10-15 min : 8 points vérif rapide
/qa-audit datalake          # 2-3 h : 10 sous-axes data quality
/qa-audit l4-final          # ~1 h : agrégation finale + verdict GO/NO-GO L4

# Tests pytest
pytest backend/tests/ -p no:schemathesis --cov=backend --cov-branch
pytest backend/tests/properties/ -v       # 135 tests Hypothesis
pytest backend/tests/test_pappers_purge_regression.py -v   # 12 tests anti-régression
pytest backend/tests/test_soda_config_valid.py -v          # 20 tests Soda
pytest backend/tests/test_sast_config_valid.py -v          # 15 tests Bandit

# Frontend
cd frontend && pnpm install && pnpm exec playwright install
pnpm test:e2e:clickables    # 1 navigateur, ~5 min
pnpm test:e2e:matrix        # 8 projets, ~30 min

# CI workflows manuel
gh workflow run qa-data-quality.yml
gh workflow run qa-mutation-testing.yml
gh workflow run qa-security.yml
gh workflow run security-redteam.yml

# QCS calcul
python ~/.claude/skills/qa-audit/scripts/qa_qcs.py \
  --current metrics.json --target L4 --format human
```

---

**Maintenu par** : qa-engineer subagent + skill `~/.claude/skills/qa-audit/`
**Dernière mise à jour** : 2026-05-03 post-Sprint 4+5
