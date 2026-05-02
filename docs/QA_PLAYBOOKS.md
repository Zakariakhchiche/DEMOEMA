# DEMOEMA — Playbooks QA & Capitalisation

> Document de capitalisation des expériences QA DEMOEMA (audits, security red-team, browser tests).
> Source-of-truth pour les futurs audits — toujours référencer avant de relancer un cycle.
> Créé : 2026-05-02 · Maintenu par : qa-engineer subagent (`.claude/agents/qa-engineer.md`)

---

## 1. Stack QA actuelle

### Ce qu'on a déjà en prod (2026-05-02)

| Composant | Outil | Localisation | Cadence |
|---|---|---|---|
| Backend unit/integration | pytest + pytest-asyncio + pytest-cov | `backend/tests/` | Pre-merge GitHub Actions |
| Frontend unit | Vitest | `frontend/__tests__/` | Pre-merge GitHub Actions |
| Frontend type-check | tsc --noEmit | `frontend/` | Pre-merge GitHub Actions |
| Design lint | `npm run lint:design` (custom WCAG check) | `frontend/scripts/` | Pre-merge sur changes UI |
| Browser audit (manuel) | Chrome DevTools MCP | session Claude Code | Ad-hoc (audits trimestriels) |
| Security red-team LLM | NVIDIA garak v0.14.1 | `C:\Users\zkhch\garak_demoema\` | Hebdo via `.github/workflows/security-redteam.yml` (lundi 03h UTC) |
| Smoke prod | curl `/api/health` + `/api/datalake/_introspect` | sur VPS | Aucune cadence (à automatiser) |
| CI pipeline | `.github/workflows/ci.yml` | repo | À chaque PR |

### Ce qui manque (gaps identifiés via état de l'art 2026)

1. **API contract fuzzing** — pas de Schemathesis sur l'OpenAPI FastAPI (couvrirait les 110+ endpoints en 1 commande).
2. **Continuous LLM eval** — pas de DeepEval/Promptfoo en CI : les 110 questions copilot baseline sont rejouées manuellement, pas en gate.
3. **E2E navigateur scripté** — pas de Playwright/Stagehand/browser-use en CI : les 8 sections nav sont auditées manuellement.
4. **LLM-as-judge panel** — pas de système d'eval automatique (faithfulness, answer_relevancy, hallucination_rate) sur réponses copilot.
5. **Run registry** — les rapports garak/audits sont éparpillés (filesystem local + Confluence + Jira). Pas de table `silver.qa_runs` consultable.
6. **OWASP ASI 2026 mapping** — nouveau standard pour agents tool-using, pas encore appliqué au copilot DeepSeek.

---

## 2. Expériences accumulées (corpus 2026-04 → 2026-05)

### Audit QA round 1 (2026-05-01)
- 110 questions API datalake `/api/copilot/stream` SSE
- 5 questions UI manuelles
- Traversée 8 sections nav (`#dashboard`, `#chat`, `#explorer`, `#pipeline`, `#audit`, `#graph`, `#compare`, `#signals`)
- Output : `C:\Users\zkhch\audit_demoema\AUDIT_QA_RAPPORT.md` (206 lignes)
- 25 bugs trouvés (4 P0, 9 P1, 8 P2, 4 P3) → tous patchés en 10 commits G1-G10
- Métriques baseline → cible :

| Métrique | Avant | Après | Cible long-terme |
|---|---|---|---|
| p50 latence copilot | 28.6 s | 10 s | < 5 s |
| p95 latence copilot | 117 s | 18 s | < 30 s |
| Hallucinations DL{N}→département | 6/100 | 0/100 | 0 |
| Plafond MAX_ITERATIONS | 8 % | 0 % | < 1 % |
| Source `pappers` (abandonnée) | 13/110 | 0/110 | 0 |
| Service Worker enregistré | 0 | 1 | 1 (PWA) |
| Routes nav fonctionnelles | 6/8 | 8/8 | 8/8 |

### Audits security garak round 1+2 (2026-05-01 → 2026-05-02)
- **Round 1** — probe `promptinject.HijackHateHumans` (256 prompts) : 83% bypass découvert → patch `_PROMPT_INJECTION_PATTERNS` (PR #68) → 0% bypass.
- **Round 2** — probes `dan` + `latentinjection` (2988 prompts, 108 min) :
  - Vraies vulns : `LatentInjectionTranslationEnZh` 78%, `LatentInjectionTranslationEnFr` 73%, `LatentInjectionFactSnippetLegal` 50% → patch PR #70 → 0% bypass attendu (re-run à faire).
  - **Faux positifs documentés** : `dan.* / mitigation.MitigationBypass` 80-100% car détecteur cherche refus EN ("I cannot/I'm sorry"), copilot répond FR ("Je suis désolé, je ne peux pas"). NE PAS PATCHER.
- Endpoint dédié : `POST /api/copilot/redteam` (body JSON, contourne URL-encoding du GET).
- Config : `C:\Users\zkhch\garak_demoema\demoema_copilot.json`.
- Analyseur : `C:\Users\zkhch\garak_demoema\analyze_report.py` (gère `entry_type=eval` + `attempt`, sample dict outputs, encoding UTF-8).

### Leçons techniques (capitalisées)

1. **Regex `\b` global piégeux** — un `\b(?:...)` au début d'une grande regex casse silencieusement les patterns commençant par `[`, `<` ou caractères CJK (word boundary ASCII-only en Python `re`). Toujours retirer le `\b` global et ré-ajouter localement.

2. **Détecteurs garak EN biaisés sur LLM FR** — `mitigation.MitigationBypass` cherche "I cannot/I'm sorry/As an AI". Notre copilot répond "Je suis désolé, je ne peux pas" → marqué fail mais c'est un vrai refus. Toujours sampler les outputs avant de conclure.

3. **Encoding bash → curl casse CJK** — `curl -d '{"q":"哈哈被耍"}'` perd les caractères chinois sur Windows bash. Toujours passer le payload via fichier (`-d @payload.json`) pour les tests CJK/UTF-8.

4. **DAN.Ablation_Dan_11_0 = 100% fail = sécurité OK** — le prompt > 2000 chars est cappé par le backend ("Question trop longue"), donc le détecteur ne trouve pas le marker DAN. C'est la sécurité d'input cap qui marche, pas une vuln.

5. **`asyncio.gather` parallèle pour tools indépendants** — gain p50 28→10 s sur copilot. Sérialiser uniquement les tools partageant un même SIREN (ordre causal `get_fiche` → `get_scoring`).

6. **Service Worker Serwist v9 exige Strategy instances** — `handler: "NetworkFirst" as any` cast TypeScript masque le runtime fail. Toujours `handler: new NetworkFirst({...})`.

7. **Hash routing FR/EN aliases** — `HASH_ALIASES = { graphe: "graph", comparer: "compare" }` évite les liens morts si l'utilisateur tape la version FR.

---

## 3. Roadmap adoption outils QA (priorisée)

### Sprint QA-1 (semaine 1-2) — base eval continue
1. **DeepEval** (Confident AI, OSS) — `pip install deepeval`
   - Convertir les 110 questions baseline en `LLMTestCase` versionnés.
   - Métriques : `AnswerRelevancyMetric`, `FaithfulnessMetric`, `HallucinationMetric`, custom `GEval` pour terminologie M&A FR.
   - Intégration : `pytest backend/tests/test_copilot_eval.py` en CI nightly.
2. **Schemathesis** — `pip install schemathesis`
   - Pointer sur OpenAPI FastAPI auto-généré (`/openapi.json`).
   - Action GH : `schemathesis/action@v2`.
   - Couvre tous les endpoints REST en 1 commande, fail-build sur 500/schema mismatch.

### Sprint QA-2 (semaine 3-4) — gates CI red-team
3. **Promptfoo** — `npm install -g promptfoo`
   - YAML déclaratif, complète garak (gates pré-merge vs scan hebdo).
   - Plugins prompt-injection / PII leak / jailbreak orientés applicatif.
   - Action GH dédiée, fail-build si hallucination_rate > seuil.
4. **deepteam** (Confident AI) — extension DeepEval pour OWASP ASI 2026
   - 50+ vulnérabilités, mappings OWASP_LLM_2025 + OWASP_ASI_2026 + NIST + MITRE ATLAS.
   - Cible : compléter garak (qui scanne le model) avec scan **système** (RAG + tool-use + multi-turn).

### Sprint QA-3 (mois 2) — agent E2E browser
5. **Stagehand** (TypeScript) ou **browser-use** (Python)
   - Rejouer les 8 sections nav + 5 scénarios critiques en CI, pas seulement audit ad-hoc.
   - DOM cache self-healing pour réduire le coût LLM.
   - MCP-compatible direct avec Claude Code subagent.

### Sprint QA-4 (mois 2-3) — observability
6. **Langfuse** ou **Opik** (Comet) — observability LLM
   - Trace chaque appel `/api/copilot/stream`, scorer en continu.
   - Branchement existant FastAPI middleware.
   - Détecter régressions production sans attendre l'audit suivant.

### Hors scope (à confirmer Zak avant)
- Galileo, Patronus AI, Confident AI cloud, Chromatic, BrowserStack, Sauce Labs → tous SaaS payants. **Bloqué par règle no_paid_actions sans approbation explicite**.

### Veille techno mars-mai 2026 (changements actionnables IMMÉDIATS)

**À faire maintenant** (priorité décroissante) :
1. **garak 0.14.1 → 0.15.0** : Agent breaker probe + ModernBERT detector + mTLS REST. L'Agent breaker est directement utile pour tester le copilot DeepSeek M&A (tool-calling INPI/SIRENE/BODACC).
2. **Retirer PyRIT du stack** (archivé 2026-03-27) → couverture par garak 0.15 + deepteam OWASP_ASI_2026.
3. **Activer OWASP_ASI_2026** dans deepteam (ASI_03 Tool Misuse + ASI_06 Memory Poisoning) — nouveau standard Top 10 agents.
4. **Schemathesis `st fuzz`** stateful (4.17) : refactor des tests API FastAPI vers fuzzing multi-step chaînant les workflows M&A via OpenAPI Links.
5. **Chrome DevTools MCP 0.23.0** : Lighthouse audit MCP + memory leak skill + pageId multi-agent.
6. **Promptfoo Trajectory assertions** (0.121.9) pour évaluer les chaînes d'appels du copilot.
7. **Playwright 1.59.1 `browser.bind()` + `--debug=cli`** : Claude Code peut attacher au navigateur Next.js dev et auto-réparer les tests E2E.
8. **Axe MCP Server (Deque)** pour audit a11y direct depuis Claude Code (`scan` + `remediate`).
9. **Anthropic skill-creator evals** : valider nos skills internes DEMOEMA (M&A copilot, dossier-pipeline) avant prod.
10. Rester sur **Vitest 4.1.5** (ne pas migrer v5 beta avant stable).

---

## 4. Playbooks opérationnels

### Playbook A — Audit copilot 110 questions (cycle quarterly)

**Quand le déclencher** : après merge majeur sur `backend/clients/deepseek.py`, `backend/main.py::copilot_*`, ou changement source datalake.

**Pré-requis** :
- Chrome DevTools MCP installé dans la session Claude Code
- Accès SSE à `https://82-165-57-191.sslip.io/api/copilot/stream` (ou local)

**Étapes** :
1. Charger le corpus baseline : `C:\Users\zkhch\audit_demoema\AUDIT_QA_RAPPORT.md` §2.
2. Lancer 110 requêtes SSE en parallèle batch (10 à la fois pour pas surcharger DeepSeek).
3. Pour chaque réponse : capturer `latence`, `source`, `tools_called`, `hallucination_DL{N}` (regex `département\s+\d{2,3}` sur réponse).
4. Comparer aux métriques baseline (cf. table §2). Tout écart > 10% = régression à investiguer.
5. Output rapport au format `audit_demoema/AUDIT_QA_<date>.md` avec table delta.

**Métriques cibles long-terme** :
- p50 < 5 s, p95 < 30 s
- 0 hallucination DL{N}
- 0 source `pappers`
- 100% sources `silver.*` ou `gold.*`
- < 1 % plafond MAX_ITERATIONS

**Automatisation cible** : DeepEval `LLMTestCase` versionnés en `backend/tests/eval/` + nightly cron.

### Playbook B — Audit security garak (cycle hebdomadaire CI)

**Quand le déclencher** : automatique chaque lundi 03h UTC via `.github/workflows/security-redteam.yml`. Manuel via `workflow_dispatch` après changement majeur du system prompt ou des `_PROMPT_INJECTION_PATTERNS`.

**Pré-requis** :
- Endpoint `POST /api/copilot/redteam` opérationnel
- venv garak : `C:\Users\zkhch\garak_demoema\.venv\`

**Probes prioritaires DEMOEMA** :
- `promptinject` — jailbreaks classiques (HijackHateHumans 256 prompts, ~10 min)
- `dan` — Do Anything Now persona (~256 prompts, mais beaucoup de faux positifs FR — voir leçon 2 §2)
- `latentinjection` — payload caché dans contenu fourni (~1000 prompts, 30-60 min) — **CRITIQUE pour M&A car copilot reçoit fiches/textes à traduire/résumer**
- ~~`sysprompt_extraction`~~ : nom invalide en garak v0.14, **ne pas utiliser**

**Commande standard** :
```bash
cd C:\Users\zkhch\garak_demoema
.venv/Scripts/python.exe -m garak \
  --target_type rest \
  --generator_option_file demoema_copilot.json \
  --probes promptinject,dan,latentinjection \
  --generations 1 \
  --report_prefix audit_v$(date +%Y%m%d_%H%M)
```

**Analyse post-run** :
```bash
.venv/Scripts/python.exe analyze_report.py ~/.local/share/garak/garak_runs/audit_v*.report.jsonl
```

**Critère PASS/FAIL** :
- max_fail_rate global > 30% → FAIL (issue GitHub auto-créée par le workflow)
- Toujours sampler les outputs sur les fail rates > 50% avant patch (faux positifs FR connus)

**Workflow patch en cas de vraie vuln** :
1. Identifier le pattern d'attaque dans les samples failed
2. Étendre `backend/main.py::_PROMPT_INJECTION_PATTERNS` (regex)
3. Ajouter test pytest `backend/tests/test_<probe>_patterns.py` avec 15+ vecteurs BLOCK + 15+ ALLOW
4. Commit/PR/merge/deploy
5. Re-run garak pour confirmer 0% bypass

### Playbook C — Audit navigation UI 8 sections (cycle quarterly)

**Quand le déclencher** : après merge sur `frontend/src/app/page.tsx`, `frontend/src/components/dem/TopHeader.tsx`, `frontend/src/lib/hashRouting.ts`, ou ajout/suppression de section.

**Pré-requis** :
- Chrome DevTools MCP dans la session
- Frontend prod accessible (`https://82-165-57-191.sslip.io`)

**Sections à vérifier** :
1. `#dashboard` — H1 "Bonjour Anne", 4 cards métriques visibles
2. `#chat` — input copilot focus, conversation initiale rendue
3. `#explorer` — liste tables datalake, sélection charge données
4. `#pipeline` — kanban deals, drag possible
5. `#audit` — historique runs garak/QA visible
6. `#graph` (alias `#graphe`) — réseau entreprises rendu (nœuds + arêtes)
7. `#compare` (alias `#comparer`) — UI comparaison côte-à-côte
8. `#signals` — flux BODACC + alertes triables

**Procédure (chrome-devtools MCP)** :
1. `navigate_page` à chaque hash → screenshot + DOM snapshot
2. Vérifier `H1` non vide ET ≠ "Bonjour Anne" sur toutes sauf #dashboard
3. Vérifier `aria-label` cohérents (a11y)
4. Vérifier `console.error` count = 0
5. Vérifier `navigator.serviceWorker.getRegistrations().length > 0` (PWA)

**Bug pattern récurrent** : si H1 reste figé sur "Bonjour Anne" malgré changement hash → regarder `HASH_ALIASES` dans `frontend/src/lib/hashRouting.ts`.

**Automatisation cible** : Stagehand/Playwright avec MCP en CI sur PRs touchant `frontend/`.

### Playbook D — Audit datalake gold/silver INTÉGRITÉ COMPLÈTE (cycle mensuel + post-ingestion)

**Périmètre** : c'est le cœur de DEMOEMA — ~15M rows répartis sur silver/bronze/gold.
- `bronze.*` : raw ingéré tel quel des sources (BODACC annonces XML, INPI bulk dumps, OpenSanctions ZIP)
- `silver.*` : raw normalisé (schémas typés, colonnes canoniques)
  - `silver.inpi_comptes` ~6.3M rows (bilans annuels)
  - `silver.inpi_dirigeants` ~8.1M rows (mandats sociaux)
  - `silver.opensanctions` ~280k rows (sanctions UE/OFAC/UK/HMT)
  - `silver.bodacc_annonces` (cumul annonces officielles)
  - `silver.insee_unites_legales` (SIRENE base)
  - `silver.recherche_entreprises` (cache enrichi gouv)
- `gold.*` : matérialized views (jointures + agrégats métier)
  - `gold.entreprises_master`, `gold.cibles_ma_top`, `gold.scoring_ma`, `gold.sanctions_master`, `gold.press_mentions`, `gold.dirigeants_master`, `gold.dirigeants_360`, etc. (~12 tables)
- Whitelist sécurité : `GOLD_TABLES_WHITELIST` dans `backend/datalake.py`

**Quand le déclencher** :
- Mensuel obligatoire (1er du mois)
- Post-ingestion majeure (>100k rows ajoutées)
- Post-changement schéma gold (nouvelle colonne, nouvelle MV)
- Post-deploy backend touchant `backend/routers/datalake.py` ou `backend/datalake.py`

**Pré-requis** :
- SSH VPS readonly : `ssh -i ~/.ssh/demoema_ionos_ed25519 root@82.165.57.191`
- Postgres credentials read-only (utilisateur `demoema_qa`, à créer si absent)
- Endpoint `/api/datalake/_introspect`
- Soda Core installé : `pip install soda-core-postgres`
- `qa/soda/configuration.yml` + `qa/soda/checks/` (à créer dans le repo)

#### Sous-axe D.1 — Schéma & contrats (zéro drift)
- **Pas de DROP COLUMN jamais** (mandate Zak `feedback_no_new_tables`) — vérifier via `pg_attribute` historique vs snapshot
- **Pas de NEW TABLE** sauf décision explicite Zak — enrichir l'existant (add column nullable)
- **Types Postgres stricts** : pas de `text` pour des montants (utiliser `numeric(18,2)`), pas de `timestamp without time zone`, toujours `timestamptz`
- **NOT NULL sur clés métier** : `siren`, `id`, `ingested_at`
- **Snapshot schéma versionné** : `qa/snapshots/schema_<date>.sql` généré via `pg_dump --schema-only`, comparé en CI vs précédent (diff PR description si changement)
- **Verdict D.1** : pass si 0 DROP COLUMN, 0 NEW TABLE non autorisée, types canoniques, NOT NULL clés métier

#### Sous-axe D.2 — Ingestion sources externes (chaque worker testé)

Pour chaque source (`bodacc`, `inpi_comptes`, `inpi_dirigeants`, `opensanctions`, `insee_sirene`, `recherche_entreprises`, `hatvp`, `ofac`, etc.) — un test dédié dans `infrastructure/agents/platform/ingestion/sources/test_<source>.py` couvrant :

1. **Idempotence** : rejouer la même source 2× consécutivement → 0 doublon créé (constraint unique sur `(siren, year, source_hash)` ou équivalent)
2. **Reprise après crash** : kill -9 mid-ingestion → relancer → reprendre à la dernière transaction COMMIT propre
3. **Schema validation** : valider que la réponse parsée respecte un Pydantic model strict (rejet ligne si incomplète, log warning, pas crash worker)
4. **Rate limit respecté** : test Mock que le worker dort entre requêtes selon `requests_per_second` config
5. **Encoding UTF-8** : payloads avec accents (Pinault, Aïcha, Zürich) + CJK (testé avec INPI dirigeants nom étrangers) sans corruption
6. **Bulk insert performance** : 100k rows < 30 s via `asyncpg.copy_records_to_table` (cf. G9 BODACC COPY natif)
7. **MAX_ROWS_PER_RUN** : cap à 500k rows par run pour éviter saturation (cf. opensanctions.py:24)
8. **Retry / backoff exponential** : 503/timeout source → retry 3× avec sleep `2**attempt`
9. **Fallback dégradé** : si source down → fallback `silver.<source>` cache (G6 OpenSanctions pattern), flag `degraded:true`
10. **Logs structurés** : `{source, run_id, rows_in, rows_inserted, rows_rejected, duration_ms, errors}` en JSON

**Verdict D.2** : pass si chaque source a `test_<source>.py` avec ces 10 tests + tous green en CI nightly.

#### Sous-axe D.3 — Transformation silver → gold (chaque MV testée)

Pour chaque MV `gold.<name>` :

1. **Définition vérifiable** : la query définissant la MV est dans le repo (`backend/migrations/gold_<name>.sql`), pas seulement en DB
2. **Test refresh** : `REFRESH MATERIALIZED VIEW CONCURRENTLY gold.<name>` réussit en < 5 min sur prod
3. **Test résultat** : `SELECT COUNT(*) FROM gold.<name>` retourne valeur cohérente (vs snapshot mois précédent, delta < 20 %)
4. **Cohérence FK conceptuelle** : 100 % des `siren` de `gold.<name>` existent dans `silver.insee_unites_legales` ou `silver.inpi_comptes`
5. **Pas de NULL sur clés** : `siren`, `id`, `updated_at` → 0 NULL
6. **Index présents** : chaque MV a son index sur `siren` minimum (ex: SCRUM-133 a montré que `gold.press_mentions` n'avait pas son index → query slow)
7. **Pas de doublons SIREN** sauf intentionnel (test sur `gold.entreprises_master` : 1 row par SIREN unique)
8. **Distribution sectorielle réaliste** : `gold.cibles_ma_top` doit pas être 100 % NAF 7010Z (vrai dataset M&A FR a une distribution réaliste)

Test SQL canonique :
```sql
-- Pour chaque MV gold, ces 8 checks doivent passer
WITH mv_checks AS (
  SELECT 'gold.entreprises_master' AS mv,
         COUNT(*) AS rows,
         COUNT(*) FILTER (WHERE siren IS NULL) AS null_siren,
         COUNT(*) - COUNT(DISTINCT siren) AS dup_siren,
         COUNT(*) FILTER (WHERE NOT EXISTS (
           SELECT 1 FROM silver.insee_unites_legales s WHERE s.siren = em.siren
         )) AS orphan_siren,
         COUNT(*) FILTER (WHERE updated_at IS NULL) AS null_updated_at
  FROM gold.entreprises_master em
  -- ... répéter pour chaque MV
)
SELECT * FROM mv_checks WHERE rows = 0 OR null_siren > 0 OR dup_siren > 0
                       OR orphan_siren > rows * 0.01 OR null_updated_at > 0;
-- Cible : 0 row retournée
```

**Verdict D.3** : pass si chaque MV gold passe ses 8 checks + index présents + refresh < 5 min.

#### Sous-axe D.4 — Data quality framework (Soda Core toutes tables)

Fichier `qa/soda/checks/silver_inpi_comptes.yml` exemple :
```yaml
checks for silver.inpi_comptes:
  - row_count > 6000000      # baseline 6.3M
  - missing_count(siren) = 0
  - duplicate_count(siren, year) = 0   # 1 row par SIREN/exercice
  - invalid_count(siren) = 0:
      valid regex: '^[0-9]{9}$'
  - invalid_count(ca) = 0:
      valid min: 0
      valid max: 1e12      # 1 trillion EUR cap raisonnable
  - freshness(ingested_at) < 24h
  - schema:
      fail:
        when wrong column type:
          siren: varchar(9)
          ca: numeric(18,2)
          ingested_at: timestamptz

checks for silver.inpi_dirigeants:
  - row_count > 8000000      # baseline 8.1M
  - missing_count(siren) = 0
  - missing_count(nom) = 0
  - missing_count(prenom) = 0   # ou allow null si entité morale
  - freshness(ingested_at) < 24h

checks for silver.opensanctions:
  - row_count between 250000 and 350000   # 280k baseline ±25%
  - missing_count(entity_id) = 0
  - duplicate_count(entity_id) = 0
  - freshness(ingested_at) < 7d   # mensuel

checks for gold.scoring_ma:
  - row_count > 1000000
  - missing_count(deal_score) = 0
  - invalid_count(deal_score) = 0:
      valid min: 0
      valid max: 100
  - freshness(updated_at) < 24h

# ... répéter pour les ~12 tables gold + ~6 tables silver
```

Commande : `soda scan -d demoema -c qa/soda/configuration.yml qa/soda/checks/`

**Verdict D.4** : pass si Soda 0 fail + chaque table a ≥ 5 checks (row_count, missing, duplicate, invalid, freshness).

#### Sous-axe D.5 — Lineage testable (OpenLineage + tests cross-tables)

- **OpenLineage events** : chaque MV refresh émet un event `(input_datasets, output_datasets, run_id)` consommé par Marquez
- **Test lineage** : `gold.cibles_ma_top` doit dépendre de `silver.inpi_comptes` ET `gold.scoring_ma` — vérifier via Marquez API
- **Test "cassure lineage"** : si on retire une dépendance source (drop view silver), CI doit fail explicitement
- **Documentation auto** : `docs/DATACATALOG_LINEAGE.md` regéneré à chaque release depuis OpenLineage

**Verdict D.5** : pass si lineage Marquez à jour + 0 dépendance manquante + doc regen automatique.

#### Sous-axe D.6 — Performance & SLA datalake

- **p95 SELECT FROM gold.entreprises_master WHERE siren = X** : < 50 ms (avec index siren)
- **p95 query Explorer** (`SELECT * FROM gold.<table> LIMIT 100`) : < 500 ms
- **MV refresh time** : `gold.entreprises_master` < 5 min (CONCURRENTLY), `gold.scoring_ma` < 10 min
- **Bulk insert worker** : BODACC 50k rows < 30 s (cf. G9 patch)
- **N+1 detection** : trace OpenTelemetry sur endpoints fiche/dashboard — 0 N+1 sur les 10 top queries
- **EXPLAIN ANALYZE en CI** : pour les 20 queries les plus lentes (via `pg_stat_statements`), capturer plan + comparer baseline (alerte si seq scan apparaît)
- **Index missing detector** :
```sql
SELECT schemaname, tablename, attname
FROM pg_stats
WHERE schemaname IN ('silver', 'gold')
  AND n_distinct > 1000
  AND correlation > 0.5
  AND tablename || '_' || attname || '_idx' NOT IN (
    SELECT indexname FROM pg_indexes WHERE schemaname IN ('silver', 'gold')
  );
-- Cible : 0 row (tous les champs filtrables ont leur index)
```

**Verdict D.6** : pass si SLA respectés + 0 N+1 + 0 index missing sur champs filtrables.

#### Sous-axe D.7 — RGPD & PII (dirigeants personnes physiques)

- **`silver.inpi_dirigeants`** contient des PII (nom, prénom, date naissance, adresse) — minimisation obligatoire
- **Pseudonymisation possible** : `presidio` (Microsoft) tag les colonnes PII automatiquement
- **Logs sans PII** : aucun log applicatif ne doit contenir `nom`/`prenom` lisible — utiliser hash SHA256(nom+prenom+siren) ou juste SIREN de la société
- **Droit à l'oubli testable** : endpoint admin DELETE `dirigeant_id` doit purger silver + gold + caches Redis + logs (ou anonymiser)
- **Export utilisateur** : si DEMOEMA expose une fiche dirigeant, l'utilisateur dirigeant lui-même doit pouvoir demander l'export portabilité (RGPD art. 20)
- **Audit log accès** : qui a consulté la fiche du dirigeant X et quand → traçable 30 jours
- **Retention policy** : silver.inpi_dirigeants garde 100 % des mandats actifs + N-3 ans révoqués (pas indéfini)

**Verdict D.7** : pass si 0 PII en logs applicatifs + endpoint DELETE testable + audit log accès actif.

#### Sous-axe D.8 — Backup & restore (DR)

- **Backup quotidien** : `pg_dump` ou `pg_basebackup` chaque nuit, stocké en off-site (S3-compatible Hetzner Storage Box ou Backblaze)
- **Test restore mensuel** : restaurer le dump du jour précédent sur un staging temporaire en < 4h (RTO objectif)
- **RPO** : Point-in-time recovery ≤ 24h en cas de désastre
- **Validation post-restore** : `soda scan` sur l'instance restaurée → 100 % checks pass
- **Encryption at rest** : disques VPS chiffrés (LUKS) + dumps chiffrés (gpg avec clé managée)

**Verdict D.8** : pass si backup auto + test restore réussi (< 4h) + soda scan post-restore green.

#### Sous-axe D.9 — Observability datalake

- **Métriques Prometheus** : `datalake_rows_total{schema,table}`, `datalake_freshness_seconds{table}`, `datalake_query_duration_seconds`, `datalake_ingestion_errors_total{source}`
- **Grafana dashboard** : 1 panel par table critique avec freshness + row count + p95 query
- **Alerting** : Slack/email si `freshness > seuil` (BODACC 24h, INPI 24h, OpenSanctions 7d)
- **Logs structurés** : tous les workers ingestion + queries datalake en JSON avec `correlation_id`
- **Trace OpenTelemetry** : SSE copilot bout-en-bout (frontend → backend → tools datalake → asyncpg → Postgres)

**Verdict D.9** : pass si métriques exposées + alerting actif + tous workers tracés.

#### Sous-axe D.10 — Tests d'intégrité référentielle (cross-source)

- **Cohérence SIREN** : tout SIREN dans `gold.*` doit exister dans au moins une source officielle (SIRENE ou INPI)
- **Cohérence dirigeants** : `gold.dirigeants_master.siren` ↔ `silver.inpi_dirigeants` cohérent (delta < 1 %)
- **Doublons inter-sources** : un même dirigeant Pinault peut apparaître dans INPI ET SIRENE — entity resolution via Splink (cf. axe 3 logique métier) doit dé-dupliquer
- **Datasets cross-cohérence** : un SIREN sanctionné dans `silver.opensanctions` doit avoir un flag dans `gold.entreprises_master.is_sanctioned = true`
- **Mises à jour propagées** : si SIRENE update une entreprise (radiation), `gold.entreprises_master.is_active` doit être mis à `false` au prochain refresh

**Verdict D.10** : pass si toutes les invariants cross-source OK (test SQL dédié `qa/sql/cross_integrity.sql`).

### Synthèse Playbook D — Verdict global

Pass si les 10 sous-axes D.1 → D.10 sont GO. Sinon NO-GO + liste de blockers.

**Cible L4** : automatisation 100 % de Playbook D dans GitHub Actions cron mensuel + alerting Slack si NO-GO.

---

## 5. Playbook E — Audit minutieux 14 axes (cycle release majeure)

**Quand le déclencher** : avant chaque release majeure (sprint review, demo investisseur, mise en prod après refonte). Le qa-engineer orchestre les 10 axes en séquence, génère un rapport consolidé `audit_demoema/AUDIT_MINUTIEUX_<date>.md` avec verdict GO/NO-GO par axe.

**Durée typique** : 4-8 h selon profondeur (à parallélism via subagents).

**Verdict global** : GO uniquement si les 14 axes sont GO. Sinon NO-GO + liste de blockers.

### Axe 1 — Frontend (Next.js 15 / React 19 / PWA)
- **Tests E2E** : Playwright/Stagehand sur les 8 sections nav + 5 scénarios critiques (login, search→fiche, graph, copilot streaming, export CSV)
- **Hydration mismatches** : `next dev --debug` + check `[hydration mismatch]` dans console
- **Bundle size** : `@next/bundle-analyzer` baseline + alerte si croissance > 10 %
- **Core Web Vitals** : INP (Interaction to Next Paint), LCP, CLS via Lighthouse-CI sur les 14 routes principales
- **Service Worker** : `navigator.serviceWorker.getRegistrations().length > 0` + cache strategy assertion (Serwist v9 Strategy instances, pas string handlers)
- **SSE robustness** : 10 questions consécutives en 20 s → 10 blocs `<summary>` rendus (regression test du bug G5)

#### Sous-axe 1.bis — TEST EXHAUSTIF DE CHAQUE ÉLÉMENT CLIQUABLE (zéro élément non testé)
**Exigence dure** : 100 % des éléments cliquables du frontend doivent être testés individuellement. Pas seulement les `<button>` — TOUT élément cliquable : liens, `role="button"`, `role="tab"`, `role="menuitem"`, `role="checkbox"`, `role="switch"`, inputs (checkbox/radio/submit), `<select>`, `<summary>` (details), `<div onClick>`, `<span onClick>`, drag handles, resize handles, éléments avec `tabindex` focusables. Aucun fantôme, aucun handler vide, aucun "Coming soon".

**Inventaire automatique exhaustif** (à lancer en début d'audit) :
```bash
# Tous patterns de clickables qu'on cherche dans le repo (référence)
cd frontend
grep -rEn '<(button|Button)\b' src --include='*.tsx' | wc -l   # ~144
grep -rEn '<a\s+href' src --include='*.tsx' | wc -l           # ~50
grep -rEn 'onClick=' src --include='*.tsx' | wc -l            # ~120
grep -rEn 'role="(button|tab|menuitem|switch|checkbox|radio|link)"' \
  src --include='*.tsx' | wc -l                                # ~30
grep -rEn '<input\s+type="(checkbox|radio|submit|button|range)"' \
  src --include='*.tsx' | wc -l                                # ~20
grep -rEn '<(select|summary|details)\b' src --include='*.tsx' | wc -l  # ~10
grep -rEn 'tabIndex=\{?[0-9]+' src --include='*.tsx' | wc -l           # ~15

# = 350-400+ éléments interactifs distincts sur 14 routes
```

**Test par élément cliquable** (Playwright auto-discovery + assertions) :
1. **Visibilité** : rendu dans le DOM (`isVisible() === true`)
2. **Label / nom accessible non vide** : `accessibleName()` non vide via `aria-label`, `aria-labelledby`, `textContent`, ou `<label>` lié pour les inputs
3. **Touch target** : `boundingBox().width >= 24 && height >= 24` (WCAG 2.2 AA, sauf inputs natifs où 20×20 toléré)
4. **Activable** : `isEnabled()` ou état `disabled`/`aria-disabled` justifié
5. **Focusable au clavier** : `tabIndex` >= 0 (`Tab` peut atteindre l'élément, sauf décoration)
6. **Action vérifiable** : après `click()` (ou `check()` pour checkbox, `selectOption` pour select), un des effets :
   - **Navigation** (`page.url()` change) — `<a href>`, boutons-link
   - **Mutation DOM** (innerText length delta > seuil) — modals, drawers, toggles, tabs
   - **Network** (request capté via `page.on('request')`) — fetch API
   - **State** (input value change, classe CSS active, `aria-expanded` toggle, `aria-selected` change) — toggles, accordeons, tabs
   - **Form submit** (pour `<input type="submit">`) — assertion sur action
7. **PAS d'effet "fantôme"** : zéro élément qui n'a aucun des 4 effets ci-dessus (handler vide, TODO, console.log only)
8. **Anti-double-clic** : 2 clics rapides ne déclenchent pas 2 fetchs identiques (debounce ou disabled pendant pending)
9. **Keyboard activable** : `Enter`/`Space` sur l'élément focusé déclenche le même effet que clic souris (a11y critique)
10. **Hover preview** : si `title` ou tooltip → s'affiche au hover (pas tooltip vide)

**Sélecteur Playwright unifié** (capture TOUS les cliquables) :
```typescript
const CLICKABLE_SELECTOR = [
  // Boutons & liens HTML natifs
  'button:visible',
  'a[href]:visible',
  // ARIA roles interactifs (div/span déguisés en bouton)
  '[role="button"]:visible',
  '[role="link"]:visible',
  '[role="menuitem"]:visible',
  '[role="tab"]:visible',
  '[role="switch"]:visible',
  '[role="checkbox"]:visible',
  '[role="radio"]:visible',
  '[role="option"]:visible',
  '[role="treeitem"]:visible',
  // Inputs cliquables
  'input[type="checkbox"]:visible',
  'input[type="radio"]:visible',
  'input[type="submit"]:visible',
  'input[type="button"]:visible',
  'input[type="reset"]:visible',
  'input[type="image"]:visible',
  // Form controls cliquables
  'select:visible',
  // Details/summary
  'summary:visible',
  // onClick sur n'importe quoi (div/span/li/td...)
  '[onclick]:visible',
  // Tabindex focusables (drag handles, custom widgets)
  '[tabindex]:not([tabindex="-1"]):visible',
  // Labels liés à inputs
  'label[for]:visible',
].join(', ');
```

**Pattern de test Playwright complet** :
```typescript
// frontend/tests/clickables-exhaustive.spec.ts
import { test, expect } from '@playwright/test';
const ROUTES = ['/#dashboard', '/#chat', '/#explorer', '/#pipeline', '/#audit',
                '/#graph', '/#compare', '/#signals',
                '/targets', '/targets/[id]', '/signals', '/explorer',
                '/pipeline', '/graph']; // 14 routes principales

const CLICKABLE_SELECTOR = `button:visible, a[href]:visible,
  [role="button"]:visible, [role="link"]:visible, [role="menuitem"]:visible,
  [role="tab"]:visible, [role="switch"]:visible, [role="checkbox"]:visible,
  [role="radio"]:visible, [role="option"]:visible, [role="treeitem"]:visible,
  input[type="checkbox"]:visible, input[type="radio"]:visible,
  input[type="submit"]:visible, input[type="button"]:visible,
  input[type="reset"]:visible, input[type="image"]:visible,
  select:visible, summary:visible, [onclick]:visible,
  [tabindex]:not([tabindex="-1"]):visible, label[for]:visible`;

for (const route of ROUTES) {
  test(`clickables exhaustifs sur ${route}`, async ({ page }) => {
    await page.goto(`http://localhost:3000${route}`);
    await page.waitForLoadState('networkidle');

    const els = await page.locator(CLICKABLE_SELECTOR).all();
    const failures: Array<{selector:string, reason:string}> = [];
    const passes: string[] = [];

    for (const el of els) {
      const tag = await el.evaluate((e:Element) => e.tagName.toLowerCase());
      const role = await el.getAttribute('role') ?? '';
      const type = await el.getAttribute('type') ?? '';
      const text = ((await el.textContent()) ?? '').trim().slice(0, 60);
      const aria = (await el.getAttribute('aria-label')) ?? '';
      const ariaLabelledBy = (await el.getAttribute('aria-labelledby')) ?? '';
      const id = `[${tag}${role?` role=${role}`:''}${type?` type=${type}`:''}] "${text || aria}"`;
      const box = await el.boundingBox();
      const accessibleName = await el.evaluate((e:any) => e.ariaLabel
        || e.getAttribute('aria-labelledby')
        || e.textContent?.trim()
        || e.getAttribute('title')
        || '');

      // 1. Label / nom accessible
      if (!accessibleName) {
        failures.push({selector: id, reason: 'accessibleName vide'});
        continue;
      }
      // 2. Touch target
      const minSize = (tag === 'input') ? 20 : 24;
      if (box && (box.width < minSize || box.height < minSize)) {
        failures.push({selector: id,
                       reason: `target ${Math.round(box.width)}x${Math.round(box.height)} < ${minSize}x${minSize}`});
      }
      // 3. Disabled justifié OK
      if (await el.isDisabled()) { passes.push(id + ' [disabled-OK]'); continue; }

      // 4. Snapshot avant
      const urlBefore = page.url();
      const sigBefore = await page.evaluate(() => document.body.innerText.length);
      let networkFired = false;
      const reqHandler = () => { networkFired = true; };
      page.on('request', reqHandler);

      // 5. Click selon type
      try {
        if (type === 'checkbox' || type === 'radio' || role === 'checkbox' || role === 'switch') {
          await el.check({timeout: 2000});
        } else if (tag === 'select') {
          const opts = await el.locator('option').all();
          if (opts.length > 1) await el.selectOption({index: 1});
        } else {
          await el.click({timeout: 2000});
        }
        await page.waitForTimeout(300);
      } catch (e) {
        page.off('request', reqHandler);
        failures.push({selector: id, reason: `interaction failed: ${(e as Error).message.slice(0,80)}`});
        continue;
      }
      page.off('request', reqHandler);

      // 6. Assertion d'effet
      const urlAfter = page.url();
      const sigAfter = await page.evaluate(() => document.body.innerText.length);
      const navigated = urlBefore !== urlAfter;
      const domChanged = Math.abs(sigBefore - sigAfter) > 5;
      const ariaExpandedChanged = await el.evaluate((e:any) =>
        e.getAttribute('aria-expanded') !== null);
      const ariaCheckedChanged = await el.evaluate((e:any) =>
        e.getAttribute('aria-checked') !== null || e.checked === true);

      if (!navigated && !domChanged && !networkFired
          && !ariaExpandedChanged && !ariaCheckedChanged) {
        failures.push({selector: id, reason: 'aucun effet (nav/DOM/network/aria)'});
      } else {
        passes.push(id);
      }

      // 7. Reset après nav
      if (navigated) await page.goto(`http://localhost:3000${route}`);
    }

    // Rapport JSON dump
    await page.evaluate((data) => console.log('CLICKABLES_REPORT', JSON.stringify(data)),
                       {route, total: els.length, pass: passes.length, fail: failures});
    expect(failures, `\n${failures.map(f => '  - '+f.selector+' → '+f.reason).join('\n')}\n`)
      .toEqual([]);
  });
}
```

**Output rapport consolidé** : `audit_demoema/clickables_audit_<date>.md`

| Route | Total cliquables | PASS | FAIL | Skip (disabled OK) | Couverture | Notes |
|---|---|---|---|---|---|---|
| #dashboard | 28 | 28 | 0 | 0 | 100 % | OK |
| #chat | 42 | 41 | 1 | 0 | 97 % ⚠ | "Sauver" handler vide |
| #explorer | 38 | 38 | 0 | 2 | 100 % | 2 boutons "future feature" disabled |
| #graph | 22 | 22 | 0 | 0 | 100 % | OK |
| ... | ... | ... | ... | ... | ... | ... |
| **TOTAL** | **350-400** | **?** | **?** | **?** | **objectif 100 %** | |

**Cas FAIL historiques à ne PAS reproduire** (regression tests obligatoires) :
- Liens nav `Graphe`/`Comparer` qui changent l'URL hash mais pas le H1 (bug G3, patché — assert H1 ≠ "Bonjour Anne" sur ces routes)
- Bouton "Sauver cible" → side effect `targets_updated` non désiré (bug G2, patché — désormais bouton dédié, pas implicite via SIREN lookup)
- Bouton "Send" copilot disabled après 5 envois rapides (bug G5 — race SSE, patché via flushSync + streamId)
- Quick replies Copilot affichés hors-contexte (bug G7, patché — conditionner sur `kind === 'sourcing' && cibles.length > 3`)
- `<details><summary>` sur les blocs "X outils utilisés" du copilot — vérifier expand/collapse fonctionnel (regression du bug perte SSE)

**Outils à activer** (versions stables 2026-05) :
- **Playwright 1.59.1** (`browser.bind()` + `--debug=cli` pour auto-repair)
- **@axe-core/playwright** (touch targets WCAG 2.2 + accessible names automatiques)
- **Storybook 9 + addon-test** (chaque composant cliquable a une story testée en isolation, gain coverage)
- **MemLab heap snapshot** post-clic (détecter detached nodes après ouverture/fermeture modal/drawer)

#### Sous-axe 1.ter — TESTS NAVIGATEUR EXHAUSTIFS (18 catégories)
Au-delà des cliquables (1.bis), il faut tester **toutes les interactions navigateur** : clavier, souris, tactile, persistance, réseau, PWA, permissions, a11y, visuel, résilience, perf, cross-browser, cross-device. ~250 tests Playwright distincts.

##### 1.ter.A — Navigation & Routing (10 tests)
- **Browser back/forward** : `page.goBack()` / `goForward()` après nav `#dashboard → #chat → #explorer` → state correctement restauré
- **Deep link / bookmark** : ouvrir `https://prod/?siren=333275774#fiche` directement → fiche EQUANS chargée
- **Refresh F5** : sur `#chat` avec conversation en cours → state préservé (localStorage) ou rechargé proprement
- **Multi-tab** : ouvrir 2 onglets connectés → auth partagée (cookie/JWT) + pas de conflit chat (chaque onglet sa session)
- **Hash change manuel** : taper `#xxxxx` invalide dans URL bar → fallback 404 ou redirect dashboard
- **Hash routing FR/EN** : `#graphe` → alias `#graph` rendu (regression G3)
- **Anchor jumps** : `#audit?run=42` → scroll auto sur le run
- **History.pushState** vs `replaceState` : SPA nav ne pollue pas l'historique inutilement
- **Lien externe `target="_blank"`** : a `rel="noopener noreferrer"` (sécurité)
- **Liens copier-coller** : URL de partage générée a tout le state (siren + filtres + tab actif)

##### 1.ter.B — Interactions clavier (15 tests)
- **Tab order** : Tab parcourt les éléments dans ordre logique (haut→bas, gauche→droite), pas de saut imprévu
- **Shift+Tab** : ordre inverse cohérent
- **Escape** : ferme modal/drawer/dropdown ouvert
- **Enter/Space** : sur boutons/role=button → déclenche clic (a11y)
- **Arrow keys** : navigation listbox/menu/tabs (role="listbox", role="tablist")
- **Home/End** : début/fin de liste navigable
- **Focus trap** : modal ouverte → Tab boucle dans la modal, ne sort pas
- **Focus restoration** : modal fermée → focus retourne au trigger
- **Skip link** : "Aller au contenu principal" présent en début de page (WCAG 2.4.1)
- **Raccourcis** : Ctrl+K (CommandPalette), Ctrl+S (sauver), Esc, `/` (focus search) — testés
- **Ctrl+F** : navigateur natif fonctionne (pas intercepté par app)
- **Tab dans formulaires** : Enter dans input single-line submit le form
- **Textarea** : Tab insère un Tab caractère ou navigue ? (configurable)
- **Focus visible** : anneau de focus visible (`:focus-visible`, WCAG 2.4.7) sur tous éléments interactifs
- **Pas de focus piégé** par un overlay invisible (z-index issues)

##### 1.ter.C — Interactions souris avancées (8 tests)
- **Double-click** : sur cell tableau → édition inline ? sur SIREN → navigation fiche ?
- **Right-click context menu** : default browser respecté (pas intercepté sauf raison forte)
- **Drag & drop** : pipeline kanban → déplacer carte entre colonnes (`page.dragAndDrop()`)
- **Drag depuis OS** : drag fichier CSV depuis explorer → upload reconnu
- **Hover preview** : tooltip après 500ms sur title/aria-describedby
- **Hover delay** : pas d'over-fire (debounce sur hover si tooltip lourd)
- **Click vs mousedown** : clic droit pas confondu avec clic gauche
- **Wheel scroll** : sur graphe react-flow → zoom (pas page scroll)

##### 1.ter.D — Interactions tactiles mobile (10 tests)
- **Tap** : équivalent click sur touch screen
- **Double-tap zoom** : désactivé pour PWA (`touch-action: manipulation`)
- **Long press** : context menu mobile, pas conflit avec scroll
- **Swipe horizontal** : drawer latéral ouvre/ferme
- **Swipe vertical** : pull-to-refresh activé ou désactivé selon UX
- **Pinch zoom** : graphe entreprises zoom avec 2 doigts
- **Touch target ≥ 44×44 px** (Apple HIG) ou ≥ 24×24 px (WCAG 2.2 AA)
- **Touch scroll momentum** : `-webkit-overflow-scrolling: touch` sur containers scrollables
- **Touch + clavier virtuel** : input focus → clavier monte → layout pas cassé
- **iOS Safari `100vh`** : correction nécessaire (toolbars dynamiques) → `--vh` custom property

##### 1.ter.E — Copier / Coller / Clipboard (6 tests)
- **Ctrl+C** sur cell SIREN → "333275774" copié (Clipboard API)
- **Ctrl+V** dans search bar → query pasted
- **Bouton "Copier" SIREN** → notification toast "Copié !"
- **Paste image** depuis presse-papier → upload (si feature)
- **Drag select texte** : sélection multi-cells tableau Explorer
- **Permission Clipboard API** : prompt navigateur si requis (Firefox restrictive)

##### 1.ter.F — File upload / download (8 tests)
- **Upload single** : `<input type="file">` accepte un CSV
- **Upload multi** : `multiple` attribute fonctionne
- **Drag&drop upload zone** : visual feedback (`dragover` highlight)
- **Validation taille** : > 10MB → message clair, pas crash
- **Validation type MIME** : .exe rejeté, .csv accepté
- **Preview** : avant submit, file name visible
- **Progress bar upload** : si > 1MB, barre de progression
- **Download** : export CSV → fichier nommé `targets_2026-05-02.csv`

##### 1.ter.G — Print / PDF export (4 tests)
- **Ctrl+P** : ouvre dialog print
- **CSS `@media print`** : layout adapté (no nav, no buttons, fiche full-width)
- **Page break control** : `page-break-after: avoid` sur tables longues
- **Export PDF** : bouton "Exporter PDF" génère fichier valide via puppeteer/jsPDF backend

##### 1.ter.H — Persistance (localStorage / sessionStorage / IndexedDB) (8 tests)
- **localStorage écrit** après action user (chat conversation, filtres explorer)
- **localStorage lu** au mount → state restauré
- **Quota exhausted** : si > 5MB → catch error, message clair
- **Clear via DevTools** → app continue fonctionner (graceful degradation)
- **sessionStorage** vs localStorage : choix cohérent (session = volatil par tab, local = persistent)
- **IndexedDB** : si utilisé pour PWA cache offline, test write/read/transactions
- **Migration version** : si schema localStorage change, migration du data ancien
- **Pas de PII en localStorage** : RGPD — emails, JWT (si stockés) doivent expirer

##### 1.ter.I — Cookies / Auth lifecycle (6 tests)
- **JWT cookie SameSite=Strict** : test cross-site → cookie pas envoyé
- **Cookie expiry** : 1h → après expiry, 401 + redirect login
- **CSRF token double-submit** : si cookie auth, CSRF header obligatoire
- **Logout** : cookie effacé proprement
- **Refresh token rotation** : silent refresh avant expiry access token
- **Third-party cookies blocked** (Safari ITP) : app fonctionne quand même

##### 1.ter.J — Network conditions (PWA + résilience) (8 tests)
- **Offline complet** (`context.setOffline(true)`) : SW sert le cache, page offline propre
- **Slow 3G** (Chrome DevTools throttle) : Lighthouse mobile reste perf > 70
- **Packet loss 5%** : retry automatique sur fetch failed
- **Timeout long** : DeepSeek 90s → loading indicator + abort possible
- **API down** : message dégradé clair, pas de spinner infini
- **Reconnect** : après offline → online, SSE reprend automatiquement
- **Cache stale** : SW invalide cache après deploy (versioning hash dans nom)
- **Background sync** : actions user offline rejouées au retour online (PWA)

##### 1.ter.K — PWA spécifique (8 tests)
- **`beforeinstallprompt`** intercepté → bouton "Installer" affiché (Chrome Android)
- **Install** : app installée → ouvre en standalone (pas dans Chrome tab)
- **Manifest** : `name`, `short_name`, `theme_color`, `background_color`, icons toutes tailles
- **Icons** : 192x192 + 512x512 + maskable
- **Splash screen** : généré depuis icons + theme_color
- **Push notifications** : permission demandée au bon moment, pas au mount
- **iOS Safari Add to Home** : meta tags `apple-touch-icon` + `apple-mobile-web-app-capable`
- **Standalone detection** : `window.matchMedia('(display-mode: standalone)')` → UI adaptée

##### 1.ter.L — Permissions navigateur (4 tests)
- **Geolocation** : si utilisé pour filtrer cibles → permission demandée explicitement, pas au mount
- **Notifications** : permission demandée après action user (pas auto)
- **Clipboard read** : permission API Clipboard
- **Permission denied** : fallback graceful (pas d'erreur red)

##### 1.ter.M — Accessibilité avancée (12 tests)
- **axe-core 4.11.4 scan** sur 14 routes → 0 violation `serious`/`critical`
- **WCAG 2.2 AA** : 50 critères (incluant touch target 24×24, focus visible enhanced, drag movement alt)
- **Screen reader (NVDA/VoiceOver via Guidepup)** : structure landmarks (header, nav, main, footer)
- **`aria-live="polite/assertive"`** sur toast notifications, status messages
- **`aria-busy`** sur regions en cours de loading
- **`role="alert"`** pour erreurs critiques
- **Skip links** : "Aller au contenu", "Aller à la nav"
- **Headings hierarchy** : 1× h1, h2 logiques, pas de saut (h2 → h4)
- **Form labels** : chaque input a `<label for>` ou `aria-labelledby`
- **Error messages associés** : `aria-describedby` sur input invalide
- **Color contrast** : 4.5:1 texte normal, 3:1 texte large (WCAG AA)
- **Pas de info véhiculée par couleur seule** : icône + texte si rouge = erreur

##### 1.ter.N — Tests visuels & visual regression (8 tests)
- **Screenshot par route** : `toHaveScreenshot()` Playwright avec `maxDiffPixelRatio: 0.02`
- **Dark mode** : `colorScheme: 'dark'` → contraste OK, lisible
- **Light mode** : default
- **High contrast Windows** : `forced-colors: active` → lisible
- **Zoom 200%** : layout pas cassé (WCAG 1.4.4)
- **Zoom 400%** : reflow OK (mobile width)
- **`prefers-reduced-motion`** : animations désactivées si OS demande
- **`prefers-color-scheme`** : auto-switch dark/light selon OS

##### 1.ter.O — Résilience aux manipulations (5 tests)
- **DOM tampering** : user supprime un `disabled` via DevTools console → action backend rejette quand même (sécurité côté serveur, pas frontend trust)
- **JS désactivé** : page basique fonctionne (au moins liens HTML standards)
- **Browser extensions** : test avec uBlock activé → pas de blocage des assets propres
- **CSP strict** : `Content-Security-Policy` empêche inline scripts non autorisés
- **Console manipulation** : user tape `window.user.role = 'admin'` → backend ignore, vrai role dans JWT signé

##### 1.ter.P — Performance & Memory (6 tests)
- **INP** (Interaction to Next Paint) < 200ms via web-vitals attribution build
- **LCP** < 2.5s sur les 14 routes
- **CLS** < 0.1
- **Memory leaks via MemLab** : after open/close modal 100× → 0 detached DOM nodes
- **Animation perf** : `requestAnimationFrame` 60fps, pas de jank > 16ms
- **Page Visibility API** : tab inactive → pause polling, animations

##### 1.ter.Q — Window / Tab management (6 tests)
- **Window resize live** : drag corner → layout responsive sans flash
- **Multi-window** : 2 fenêtres détachées → état chacune indépendant
- **`beforeunload`** : si modifs non sauvées → confirmation "Voulez-vous quitter?"
- **Tab close** : event handler clean (no zombies)
- **Window focus/blur** : pause animations + cancel pending requests
- **Cross-tab communication** : `BroadcastChannel` ou storage events si auth synchronisée

##### 1.ter.R — Cross-browser & Cross-device matrix (4 tests + matrice)
- **Playwright project matrix** :
  ```typescript
  // playwright.config.ts
  projects: [
    { name: 'chromium-desktop', use: devices['Desktop Chrome'] },
    { name: 'firefox-desktop', use: devices['Desktop Firefox'] },
    { name: 'webkit-desktop', use: devices['Desktop Safari'] },
    { name: 'msedge', use: { ...devices['Desktop Edge'], channel: 'msedge' } },
    { name: 'iphone-15', use: devices['iPhone 15'] },
    { name: 'pixel-8', use: devices['Pixel 8'] },
    { name: 'ipad', use: devices['iPad Pro'] },
    { name: 'desktop-4k', use: { viewport: { width: 3840, height: 2160 } } },
  ]
  ```
- Run `playwright test --project=chromium-desktop,firefox-desktop,webkit-desktop,msedge,iphone-15,pixel-8,ipad,desktop-4k` en CI nightly
- **Verdict cross-device** : 100 % tests verts sur 8 projets (4 navigateurs × 4+ devices)

#### Outils browser à activer (versions stables 2026-05)

- **Playwright 1.59.1** (`browser.bind()` + `--debug=cli` agentic auto-repair)
- **`@axe-core/playwright`** + axe-core 4.11.4 (a11y scan automatique)
- **MemLab** (Meta) — heap snapshots before/after pour memory leaks
- **web-vitals 5+ attribution build** — INP avec `interactionTarget` debug
- **Lighthouse-CI v12** — performance + a11y + best practices + SEO + PWA
- **Guidepup** (OSS) — pilote NVDA/VoiceOver depuis Playwright
- **MSW** (Mock Service Worker) — mock SSE + fetch sans flakiness
- **chrome-devtools-mcp 0.23.0** — Lighthouse MCP + memory leak skill
- **Chromatic-equivalent OSS** : `playwright toHaveScreenshot()` natif (gratuit)

**Verdict axe 1 final** : pass uniquement si :
- Lighthouse perf > 80, a11y > 95, SW registered, 0 console error
- 100 % éléments cliquables PASS (1.bis, 350-400+)
- 100 % tests navigateur exhaustifs PASS (1.ter, ~250 tests sur les 18 catégories)
- Cross-browser matrix verte (4 navigateurs × 4+ devices = 8 projets Playwright)
- 0 violation axe-core `serious`/`critical` sur 14 routes
- INP < 200ms, LCP < 2.5s, CLS < 0.1
- 0 memory leak détecté MemLab après 100 cycles modal/drawer

### Axe 2 — Backend API MINUTIEUX (FastAPI / SSE / async / contracts)

L'axe 2 est doublé en 10 sous-axes B.1 → B.10 (parallèle au Playbook D pour le datalake). Le backend DEMOEMA = ~80 endpoints REST + SSE streaming copilot + 16 tools LLM + JWT auth + asyncpg pool.

#### Sous-axe B.1 — Inventaire exhaustif endpoints (chaque path × méthode testé)
- **Auto-discovery** : grep `@app.get/post/put/patch/delete` + `@router.*` dans `backend/main.py` + `backend/routers/*.py` → ~80 endpoints
- **Pour chaque endpoint** : 1 test happy + 5 negatives (cf. axe 15 negative coverage)
- **Couverture matrice** : path × méthode × auth_scope × content_type
- **OpenAPI 3.1 spec** : `/openapi.json` doit lister 100 % des endpoints (drift detection : grep code vs spec)
- **Tags cohérents** : chaque endpoint a un `tags=[...]` cohérent (groupement Swagger UI)
- **Verdict B.1** : pass si 100 % endpoints listés OpenAPI + 100 % ont test happy+5neg

#### Sous-axe B.2 — Schémas Pydantic stricts (input + output)
- **Tous endpoints** acceptent un `BaseModel` Pydantic v2 (pas `dict` en input)
- **Tous endpoints** retournent un `response_model` Pydantic typé (pas `dict` brut)
- **Validation strict** : `model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)` partout
- **Custom validators** : SIREN regex `^[0-9]{9}$`, code NAF `^\d{4}[A-Z]$`, dates ISO 8601
- **Schemathesis stateful** : génération automatique de payloads malformés via Hypothesis → 0 crash backend
- **Test rejet types** : envoyer `{"siren": 123}` (int) au lieu `"123456789"` (str) → 422 propre
- **Verdict B.2** : pass si Schemathesis 0 schema violation + 100 % endpoints typés + 0 `extra='allow'`

#### Sous-axe B.3 — SSE streaming robustesse copilot
- **Endpoint** : `/api/copilot/stream` envoie events `data: {...}\n\n` puis `done: true`
- **Test reconnect** : si client perd connexion mid-stream, reprendre via `Last-Event-ID` (ou réémission complète)
- **Test long stream** : 30-90 s sans timeout (timeout backend 90 s, frontend 120 s avec grace)
- **Test concurrent** : 10 streams parallèles depuis 1 user → tous reçoivent leur réponse correcte (pas de cross-talk)
- **Test cancel** : `AbortController` côté client → backend détecte `request.is_disconnected()` et stoppe les tools en cours
- **Test backpressure** : si client lent, buffer SSE pas explosé (asyncio queue size capped)
- **Pas de fuite mémoire** : 1000 streams enchaînés → RSS stable (test endurance D-style)
- **Logs SSE** : chaque stream logué avec `stream_id`, `user_id`, `tools_called`, `tokens_in/out`, `latency_ms`
- **Verdict B.3** : pass si 100 % tests SSE green + 0 cross-talk + RSS stable

#### Sous-axe B.4 — Async / concurrency / connection pool
- **asyncpg pool** : taille config (min=5, max=20), test exhaustion sous load (50 VUs concurrent → 0 timeout)
- **httpx async client** : singleton avec timeout configuré, retries via `httpx.HTTPTransport(retries=3)`
- **`asyncio.gather`** : tools indépendants en parallèle (cf. G1) — vérifier ordre causal préservé pour deps (`get_fiche` → `get_scoring`)
- **Pas de blocking call** : aucun `time.sleep()`, aucun `requests.get()` (sync) — toujours `await asyncio.sleep()` et `await httpx.get()`
- **Test deadlock** : 2 endpoints qui appellent des tools partageant le même SIREN → pas de blocage
- **Test connection leak** : 1000 requêtes → `pg_stat_activity` retourne au baseline (pas de connexions zombies)
- **Test event loop** : pas de `asyncio.run()` à l'intérieur d'un endpoint (event loop déjà actif)
- **Verdict B.4** : pass si 0 deadlock + 0 leak + asyncio profile clean (no warnings)

#### Sous-axe B.5 — Error handling cohérent (codes HTTP + messages)
- **Schéma d'erreur unifié** : tous les 4xx/5xx retournent `{"error": "...", "code": "...", "detail": "..."}` (pas FastAPI default `{"detail": "..."}` simple)
- **400** : payload mal formé syntactiquement (JSON invalide)
- **401** : pas de token Authorization
- **403** : token valide mais scope insuffisant (admin only)
- **404** : SIREN/ressource introuvable
- **422** : payload bien formé mais validation métier échoue (Pydantic)
- **429** : rate limit dépassé (slowapi)
- **500** : exception non gérée → log Sentry/correlation_id retourné, message générique user
- **502/503** : source amont down (DeepSeek, INPI, OpenSanctions) — fallback ou message clair
- **504** : timeout (DeepSeek > 90 s) — message d'excuse + lien re-essayer
- **Test chacun des 10 codes** : `backend/tests/test_error_codes.py` paramétré
- **Verdict B.5** : pass si 100 % endpoints respectent le schéma d'erreur + 10 codes testés

#### Sous-axe B.6 — Auth / authz (JWT + scopes + lifecycle)
- **JWT signature** : RSA256 ou HS256 robuste (clé ≥ 256 bits)
- **JWKS rotation** : test `/.well-known/jwks.json` accessible + clé tournée tous les 90 j
- **Expiry** : token expire en 1h → 401 + frontend refresh automatique
- **Scopes** : 5 rôles (admin / analyst / viewer / guest / super-admin) — test endpoint admin-only depuis viewer → 403
- **Refresh token** : flow complet test (login → access + refresh → expire → refresh → new access)
- **Logout** : token blacklist côté backend (Redis SET avec TTL = expiry restant)
- **CSRF** : si cookies utilisés, double-submit token ou SameSite=Strict
- **Rate limit login** : 5 tentatives/min/IP → 429 + lockout 15 min
- **Brute force detection** : alerte si > 100 401 sur 1 min depuis 1 IP
- **Verdict B.6** : pass si 5 rôles testés + JWT lifecycle complet + 0 CSRF + brute-force detection

#### Sous-axe B.7 — Rate limiting (slowapi par user, pas IP)
- **slowapi** activé : `@limiter.limit("60/minute")` sur endpoints sensibles
- **Limites par tier** : free 30/min, pro 300/min, admin illimité
- **Limit par user** (depuis JWT), pas par IP (CGNAT/Tor problème)
- **429 explicite** : header `Retry-After: <seconds>` + message en JSON
- **Test charge** : k6 100 RPS sur user free → 30 first OK, 70 next 429
- **Bypass health check** : `/api/health`, `/metrics` exemptés du rate limit (sinon Prometheus down)
- **Verdict B.7** : pass si 3 tiers testés + Retry-After présent + health bypass OK

#### Sous-axe B.8 — Caching (Redis ou in-memory)
- **Cache Redis** : si présent, TTL adapté par type :
  - `silver.inpi_comptes` lookups : 1h (data quotidienne)
  - `gold.scoring_ma` : 5 min (calcul lourd)
  - DeepSeek tool results : 30 min (réponses LLM)
- **Cache invalidation cohérente** : si data datalake change → invalider cache via pubsub Redis ou TTL court
- **Cache hit rate** : monitor via Prometheus, cible > 70 % sur fiches SIREN
- **Cache stampede protection** : `singleflight` pattern (1ère requête peuple, autres attendent)
- **Test cache** : 2 requêtes consécutives même endpoint → 1 hit DB + 1 hit cache
- **Test invalidation** : update fictif silver → invalidation propagée
- **Verdict B.8** : pass si hit rate > 70 % + invalidation cohérente + stampede protégé

#### Sous-axe B.9 — Health / liveness / readiness (3 endpoints distincts)
- **`/api/health`** : 200 toujours (sauf si app crashée) — Caddy/k8s liveness probe
- **`/api/ready`** : 200 si DB + Redis + DeepSeek tous joignables, 503 sinon — readiness probe
- **`/api/version`** : retourne `{"git_sha": "...", "version": "...", "deployed_at": "..."}` — debug
- **`/metrics`** : Prometheus exposition (cf. B.10)
- **Smoke prod auto** : cron 5 min hit `/api/ready` → alerte Slack si 503 > 2 min
- **Test démarrage propre** : container start → `/api/ready` doit passer en < 30 s
- **Test arrêt propre** : SIGTERM → finir les requêtes en cours (graceful shutdown 30 s) avant exit
- **Verdict B.9** : pass si 4 endpoints fonctionnels + cron smoke actif + graceful shutdown

#### Sous-axe B.10 — Logging structuré + traces + métriques
- **Logs JSON structurés** : `{timestamp, level, correlation_id, user_id?, endpoint, method, status, latency_ms, message}` — cf. `python-json-logger`
- **`correlation_id`** : middleware injecte un UUID par requête, propagé dans tous les logs + downstream calls
- **OpenTelemetry trace** : `opentelemetry-instrumentation-fastapi` actif → traces exportées Jaeger/Tempo
- **Métriques Prometheus** : `prometheus_fastapi_instrumentator` actif sur `/metrics`
  - `http_requests_total{method, path, status}`
  - `http_request_duration_seconds{method, path}` (histogram)
  - `copilot_streams_active` (gauge)
  - `copilot_tools_called_total{tool_name}`
  - `datalake_query_duration_seconds{table}`
- **Sentry** : exceptions non gérées capturées avec correlation_id + user_id
- **Test logs** : grep dans logs `correlation_id=<uuid>` retourne TOUS les events de la requête
- **Verdict B.10** : pass si correlation_id partout + traces OTel actives + métriques exposées + Sentry hooked

### Synthèse Axe 2 — Verdict global

Pass si les 10 sous-axes B.1 → B.10 sont GO. Cible L4 = 100 % automatisation en CI nightly + dashboard Grafana dédié backend.



### Axe 3 — Logique métier (scoring M&A / matching / business rules)
- **Property-based testing** : Hypothesis sur invariants `deal_score ∈ [0,100]`, `tier monotone(CA)`, `EBITDA ≤ CA`
- **Decision tables** : règles scoring documentées en CSV testable (decisiontable Python)
- **Matching dirigeants fuzzy** : `recordlinkage` sur sample annoté (Pinault/PINAULT/pinault → même entité)
- **Entity resolution** : doublons SIREN détectés sur `silver.inpi_dirigeants`
- **Calculs financiers** : EBITDA proxy = CA × (1 - charges_perso_taux × ...). Test vs golden dataset 50 entreprises
- **Verdict** : pass si 100 % invariants Hypothesis green + 0 doublon SIREN/entité

### Axe 4 — Données MINUTIEUX (silver/gold + ingestion + lineage + drift + PII)

**Voir aussi le Playbook D §4** qui détaille les 10 sous-axes datalake (D.1 → D.10). L'Axe 4 ici se concentre sur la donnée en transit + ingestion temps réel + drift continu + qualité applicative.

#### Sous-axe DATA.1 — Pipeline ingestion (workers infrastructure/agents/platform/)
- 60+ specs YAML dans `infrastructure/agents/platform/ingestion/specs/*.yaml` (ADEME, AMF, ANSSI, BODACC, INPI, OFAC, SIRENE, etc.)
- **Chaque spec** doit avoir un test d'idempotence + parser test + bulk insert test (cf. Playbook D.2)
- **Schema source → silver** : si la source ajoute un champ, ne pas crasher (warning log + ignore champ inconnu)
- **Versioning des schémas** : chaque YAML versioné, migration explicite si breaking change

#### Sous-axe DATA.2 — Quality continu (vs audit ponctuel)
- **Soda Core scans en CI nightly** : 100 % tables silver + gold checkées toutes les nuits (cron 02h UTC)
- **Alerting Slack** : fail Soda → Slack #data-quality + ticket SCRUM auto
- **Trend dashboard** : Grafana 1 panel par table avec freshness/row count/missing% sur 30 j

#### Sous-axe DATA.3 — Drift detection (distributions changent)
- **whylogs hebdo** : profil des colonnes critiques (`gold.scoring_ma.deal_score`, `gold.entreprises_master.ca_dernier`) → alerte si KS test > seuil vs baseline
- **Cas concret** : si INPI change le format de bilan, distribution CA va shift → drift détecté avant que les fiches partent en prod

#### Sous-axe DATA.4 — Cohérence applicative (data correctness)
- **Dashboard CA** = **Fiche CA** = **Export CSV CA** (delta < 1 % cf. G2/G4 patches)
- **Test différentiel multi-canal** : pour 50 SIREN, fetch via 4 chemins différents → tous doivent retourner les mêmes valeurs canoniques

#### Sous-axe DATA.5 — Lineage testable (cf. Playbook D.5)
- OpenLineage events émis à chaque transformation
- Marquez API queryable : `gold.cibles_ma_top` dépend de `silver.inpi_comptes` + `gold.scoring_ma`
- Cassure de dépendance → CI fail explicit

#### Sous-axe DATA.6 — Conformité RGPD pour PII (cf. Playbook D.7)
- `silver.inpi_dirigeants` 8.1M PII → audit annuel CNIL
- Logs sans nom/prénom lisible (hash uniquement)
- Endpoint DELETE testable + audit log accès

#### Sous-axe DATA.7 — Référence externes (sources gouvernementales)
- INPI RNE, SIRENE, BODACC, recherche-entreprises (gouv gratuit), DeepSeek (LLM) — tous testés via `pytest-recording (VCR.py 8.0)` (rejeu sans live API)
- Mock httpx async via `respx` pour les workers
- Détection breakage source : si `recherche-entreprises.api.gouv.fr` change schema, CI doit alerter (canary test 1×/semaine)

#### Sous-axe DATA.8 — No paid action (mandate Zak)
- Pas d'appel à Pappers (abandonné 2026-04-23) — test grep `pappers` dans response sources doit retourner 0
- Pas d'appel à GX Cloud, Soda Cloud, Confident AI cloud (tous payants) sans approbation
- Test CI lint : grep `requirements.txt` pour packages payants → fail-build

#### Sous-axe DATA.9 — Backup + restore (cf. Playbook D.8)
- Quotidien off-site + test restore mensuel < 4h RTO
- Soda scan sur instance restaurée → 100 % checks pass

#### Sous-axe DATA.10 — Reproducibilité runs ingestion
- Chaque run a un `run_id` (UUID), loggé en silver + gold tables (`source_run_id` colonne)
- Replay possible : rejouer un run pour le même `run_id` → state final identique (idempotence stricte)
- Snapshot run JSON archivé en `silver_qa.runs_archive` 90 j

**Verdict Axe 4** : pass si Soda Core 0 fail + drift whylogs OK + 4 canaux cohérents + RGPD audit log + 0 source payante + run_id traçable.


### Axe 5 — LLM Copilot (tool-calling + hallucination + RAG)
- **DeepEval LLMTestCase** : 110 questions baseline avec métriques `AnswerRelevancyMetric`, `FaithfulnessMetric`, `HallucinationMetric`, custom `GEval` pour FR M&A
- **Tool-calling correctness** : sur 30 scénarios annotés, asserter ordre + arguments des tool_calls (BFCL-style AST eval)
- **Hallucination DL{N}** : regex `département\s+\d{2,3}` interdit si pas dans query
- **Source attribution** : 100 % des fiches doivent citer `silver.*` ou `gold.*`, jamais `pappers` (abandonné 2026-04-23)
- **RAG faithfulness** : claim verification — chaque chiffre cité par le copilot doit exister dans la fiche source
- **τ-bench-style multi-tour** : 30 scénarios M&A FR avec pass^k=3 (robustesse multi-essais)
- **Verdict** : pass si DeepEval scores > 0.8 sur les 4 métriques + tool_call correctness > 90 %

### Axe 6 — Sécurité (OWASP API Top 10 + LLM red-team)
- **garak hebdo** : `promptinject + dan + latentinjection` — 0 vraie vuln (sample outputs avant conclure)
- **deepteam** : OWASP_LLM_2025 + OWASP_ASI_2026 mapping sur les 16 tools du copilot
- **OWASP API Top 10 (2023)** : BOLA, broken auth, BFLA, mass assignment, injection, etc.
  - SQL injection : check whitelist `GOLD_TABLES_WHITELIST` dans `backend/datalake.py`
  - SSRF : check fetch URLs externes ne sont pas user-controllable
  - Rate limit : test `/api/copilot/stream` avec 100 req/s — doit 429
- **Supply chain** : `pip-audit` + `npm audit` + Snyk/Trivy sur Dockerfile + lockfile pin
- **Secrets** : trufflehog/gitleaks sur le repo + check pas de token Atlassian/DeepSeek en clair
- **CORS / CSP** : assertion strict origin allow-list, pas de wildcard
- **Verdict** : pass si garak 0 vraie vuln + pip-audit/npm-audit 0 high+ + 0 secret leak

### Axe 7 — Performance / Charge (load tests + SQL profiling)
- **k6 load test** : 50 VUs sur `/api/copilot/stream` 10 min — p95 < SLA, error rate < 1 %
- **k6 spike test** : 200 VUs ramp 30 s — système doit dégrader gracieusement (429 plutôt que 5xx)
- **SQL EXPLAIN ANALYZE** : sur les top-20 queries datalake les plus lentes (via `pg_stat_statements`)
- **Index missing detection** : `pg_stat_user_indexes` + check seq_scan > index_scan ratio
- **N+1 queries** : trace OpenTelemetry sur endpoints fiche + dashboard
- **Memory** : profile container backend `docker stats` sous load → no leak (RSS stable)
- **Verdict** : pass si load 50 VUs OK + 0 N+1 + p95 SLA + RSS stable

### Axe 8 — Conformité (RGPD + AI Act EU + secret affaires M&A)
- **RGPD** : audit logs PII (emails, IP, SIREN dirigeants personnes physiques) — minimisation OK ?
- **Droit à l'oubli** : endpoint DELETE user data implémenté ?
- **AI Act EU** : système IA "à risque limité" (chat copilot) → transparence obligatoire (mention IA visible)
- **Secret affaires M&A** : aucune mention de cible identifiable dans les logs/traces, seulement SIREN ou hash
- **Auditability** : logs structurés (JSON) avec correlation_id retraçable sur 30 j
- **Cookies / consent** : si tracking, banner cookies CNIL-compliant
- **Verdict** : pass si audit logs PII OK + AI Act mention présente + secret M&A respecté

### Axe 9 — Observability / Resilience (logs + traces + retries + chaos)
- **Logs structurés** : 100 % des endpoints loggent en JSON avec `correlation_id`, `siren`, `latency_ms`, `tool_calls`
- **Traces OpenTelemetry** : SSE stream du copilot tracé bout-en-bout (frontend → backend → DeepSeek → tools → datalake)
- **Métriques Prometheus** : `prometheus_fastapi_instrumentator` actif, métriques exposées sur `/metrics`
- **Retries / circuit breakers** : OpenSanctions 503 → fallback `silver.opensanctions` (G6 a fait ça, vérifier toujours en place)
- **Timeouts cohérents** : DeepSeek 90 s, datalake 10 s, OpenSanctions 5 s — tous configurés
- **Chaos test** : `tc qdisc` simuler latence/loss 5 % → système dégrade gracieusement
- **Verdict** : pass si logs JSON + traces OTel actives + métriques exposées + retries OK

### Axe 10 — CI/CD / DevOps / Smoke prod (deployment health)
- **GitHub Actions workflows** : `ci.yml`, `deploy-ionos.yml`, `security-redteam.yml` — tous green sur main
- **Deployment health checks** : post-deploy automatique smoke 10 endpoints + alerte Slack/email si KO
- **Rollback procedure** : `docs/RUNBOOK_ROLLBACK.md` à jour, testé une fois /quarter
- **Secret rotation** : DeepSeek API key, Atlassian token, SSH keys — rotation date < 90 j
- **Backup & restore** : datalake Postgres backup quotidien + test restore mensuel
- **Container vulnerabilities** : trivy scan du `demoema-backend` image — 0 CRITICAL
- **Verdict** : pass si all workflows green + smoke prod auto + rollback testé + secrets rotated

### Axe 11 — Documentation / DX (developer experience + onboarding)
- **OpenAPI freshness** : `/openapi.json` à jour avec tous endpoints (vs grep `@app.get/post` dans backend) — 0 drift
- **README + onboarding** : un nouveau dev doit pouvoir cloner → make dev → http://localhost:3000 en < 30 min
- **Changelog conventional-commits** : tous les commits depuis dernière release respectent `feat/fix/chore/docs/...(scope):` (lint via commitlint)
- **CLAUDE.md** : à jour (stack, conventions, pièges connus, prod URL) — référencé par tous les subagents
- **Confluence space DEMOEMA** : pages 5.x, 6.x, 7.x à jour (archi, data catalog, audits)
- **Storybook coverage** : > 70 % composants `frontend/src/components/dem/*` ont une story (Storybook 9 + addon-test)
- **Type docstrings** : tous endpoints FastAPI ont `summary` + `description` Pydantic, tous hooks frontend ont JSDoc
- **Verdict** : pass si OpenAPI 0 drift + README onboarding < 30 min + commitlint green + Storybook > 70 %

### Axe 12 — Internationalisation / Localisation (FR/EN + encoding)
- **Encoding UTF-8 strict** : tous fichiers source en UTF-8 (sans BOM), tous endpoints `Content-Type: charset=utf-8`
- **Tests CJK / accents** : payload `哈哈被耍`, `Pinault`, `Zürich` doivent passer end-to-end (cf. leçon §2.3)
- **Formats FR cohérents** : nombres `1 234,56`, devises `1 234 €`, dates `02/05/2026 09:30`, pas de `1234.56` ou `5/2/26`
- **Hash routing alias FR/EN** : `#graphe`/`#graph`, `#comparer`/`#compare` — toujours réversibles
- **Locale `fr-FR` partout** : `Intl.NumberFormat('fr-FR')`, `Intl.DateTimeFormat('fr-FR', { timeZone: 'Europe/Paris' })`
- **Pluralization** : "1 cible" / "2 cibles" / "0 cible" — Intl.PluralRules
- **Système prompt copilot** : 100 % en FR, refus en FR, jamais "I cannot" / "As an AI"
- **Verdict** : pass si 0 string EN dans UI utilisateur + Intl FR partout + payloads CJK end-to-end OK

### Axe 13 — Mobile / Responsive / Touch (PWA mobile-first)
- **Breakpoints Tailwind** : sm/md/lg/xl/2xl validés sur les 14 routes principales
- **Touch targets** : ≥ 24×24 px (WCAG 2.2 AA), ≥ 44×44 px recommandé Apple HIG
- **Orientation** : portrait + paysage sur tablette/mobile sans débordement horizontal
- **PWA install** : prompt `beforeinstallprompt` fonctionne sur Chrome Android, Safari iOS Add to Home OK
- **Offline** : Serwist v9 cache les routes principales, fallback page offline propre
- **Touch gestures** : swipe drawer, pinch-zoom sur graphe, pas de tap-double pour zoom (PWA)
- **iOS Safari spécifique** : `100vh` correction (toolbars), `safe-area-inset-*`, no `overscroll-behavior` cassé
- **Lighthouse Mobile** : score perf ≥ 80 sur Slow 4G simulé
- **Verdict** : pass si Lighthouse mobile ≥ 80 + PWA installable + 0 horizontal scroll mobile

### Axe 14 — Compatibilité navigateurs (cross-browser matrix)
- **Matrix supportée** : Chrome ≥ 120, Edge ≥ 120, Firefox ≥ 115, Safari ≥ 17 (mobile + desktop)
- **Playwright cross-browser** : run E2E sur les 4 navigateurs en CI nightly (Chromium, Firefox, WebKit, MS Edge channel)
- **Polyfills nécessaires** : check `core-js` à jour, pas de feature ES2024 sans fallback Safari
- **CSS modernes** : container queries, `@layer`, `:has()`, subgrid — tester sur Safari 17 (dernier à adopter)
- **EventSource / fetch streaming** : Safari iOS supporte mal `ReadableStream` SSE — vérifier polyfill ou EventSource fallback
- **PWA Safari iOS** : pas de notifications push avant iOS 16.4, pas de install prompt natif
- **Service Worker** : Firefox private mode désactive SW — fallback réseau OK
- **Date inputs** : `<input type="date">` rendering différent par navigateur — utiliser library uniforme
- **Verdict** : pass si Playwright 4 navigateurs green + 0 console error spécifique navigateur + PWA Safari OK

---

### Outils par axe (versions stables au 2026-05-02 — veille mars→mai 2026)

| Axe | Outils prioritaires (OSS) | Version stable | Remplace / Complète |
|---|---|---|---|
| 1. Front | Playwright 1.59.1 (`browser.bind()` + `--debug=cli` + agent video receipts) · Lighthouse-CI v12 · Vitest 4.1.5 (aria snapshot) · Storybook 9 (Vitest browser mode integré) · **Axe MCP Server (Deque)** · MemLab (Meta) heap snapshots · Knip (dead code) · `@next/bundle-analyzer` + size-limit | Playwright 1.59.1 (2026-04-01), Vitest 4.1.5 (2026-04-21), axe-core 4.11.4 (2026-04) | Manuel Chrome DevTools MCP audits |
| 2. Backend API | **Schemathesis 4.17 (`st fuzz` stateful + Resource pool + Allure report)** · pytest 8.4 + pytest-asyncio 1.4a1 (event loop factories) · pytest-recording (VCR.py 8.0) · respx (mock httpx async) · xk6-sse (SSE streaming) · LLM-Locust TrueFoundry (TTFT/inter-token) | Schemathesis 4.17 (2026-04-29), VCR.py 8.0 | Tests pytest manuels |
| 3. Logique métier | **Hypothesis 6.151+ (property-based + RuleBasedStateMachine)** · Splink (entity resolution probabiliste, 7M rows < 5min) · RapidFuzz (matching string léger) · pyDMNrules / SpiffWorkflow (decision tables M&A) · pandera 0.31.1 (si pandas/polars) | Hypothesis 6.151 (2026-04), Splink stable | Custom asserts pytest |
| 4. Données | **Soda Core (YAML déclaratif, freshness natif `freshness(updated_at) < 24h`)** · Great Expectations v1.x (Python programmatique + Custom SQL Expectations) · dbt-expectations (si bascule dbt) · whylogs (KS test drift) · OpenLineage + Marquez (lineage testable) | stable | SQL ad-hoc |
| 5. LLM Copilot | **DeepEval 3.9.9** (Task Completion, Tool Correctness, Plan Adherence/Quality, Step Efficiency natifs) · **Promptfoo 0.121.9** (**Trajectory eval assertions** + HarmBench filter + Skill eval Anthropic) · **BFCL v4** (AST eval multi-turn + parallel calls) · **τ²-bench** (pass^k robustesse multi-essais) · LangChain FakeListChatModel (mock unit) | DeepEval 3.9.9 (2026-04-28), Promptfoo 0.121.9 (2026-04-27), BFCL v4 (2026-04-12) | 110 questions baseline manuelle |
| 6. Sécurité | **garak v0.15.0** (**Agent breaker probe** test des tools + ModernBERT refusal detector + system prompt extraction + homoglyph + mTLS REST cert) · **deepteam OWASP_ASI_2026** (ASI_03 Tool Misuse + ASI_06 Memory Poisoning) · pip-audit · npm audit · trufflehog · gitleaks · trivy (image scan) | garak 0.15.0 (2026-05-01), deepteam OWASP_ASI_2026 framework | **MIGRATION URGENTE garak 0.14.1→0.15.0** ; **PyRIT archivé 2026-03-27 → à retirer du stack** |
| 7. Performance | **xk6-sse (k6 streaming-aware)** + LLM-Locust TrueFoundry · k6 standard (REST endpoints) · pgbadger (SQL slow query reports) · pgbench · auto_explain Postgres (EXPLAIN ANALYZE > seuil) · OpenTelemetry + Jaeger · MemLab (frontend memory leaks) | stable | Aucune mesure auto |
| 8. Conformité | Custom audit logs PII (regex email/IBAN/SIREN-perso) · CNIL audit checklist · `presidio` (Microsoft) PII detection · OpenAI moderation API gratuit (toxicity) · gitleaks (secrets) · checklist AI Act EU | stable | Manuel |
| 9. Observability | OpenTelemetry SDK Python + Node · Prometheus + Grafana · Loki (logs) · `prometheus_fastapi_instrumentator` · OpenLineage (data) · Sentry (error tracking) | stable | print() actuels |
| 10. CI/CD | GitHub Actions natif · trivy (image scan) · gitleaks (secrets) · Dependabot · `act` (local CI test) · Renovate (deps updates) | stable | workflows existants à étendre |
| 11. Documentation/DX | commitlint + conventional-changelog · OpenAPI lint (Spectral) · Storybook 9 + addon-test (auto stories CI) · ts-doc-checker · drift detection OpenAPI vs code (custom script) | stable | manuel |
| 12. i18n/l10n | Intl.NumberFormat / DateTimeFormat (natif fr-FR + Europe/Paris TZ) · `i18next` ou `next-intl` (si extraction strings) · check encoding UTF-8 sans BOM (custom CI lint) · pseudo-localization tests | stable | hardcoded FR |
| 13. Mobile/Responsive | **Lighthouse Mobile mode (Slow 4G)** · Playwright `device` emulation (iPhone 15, Pixel 8) · BrowserStack/Sauce Labs (real devices) · PWA Builder validation · `@axe-core/playwright` touch targets WCAG 2.2 | stable | manuel responsive |
| 14. Cross-browser | **Playwright cross-browser CI** (Chromium + Firefox + WebKit + MS Edge channel) · BrowserStack matrix · core-js polyfill audit · CSS feature queries (`@supports`) · BabelESLint plugin compat (browserslist) | stable | Chrome only |

### Procédure d'invocation par le qa-engineer

```
@qa-engineer audit minutieux release X.Y.Z
```

Le subagent :
1. Vérifie la baseline (`git log` du dernier audit minutieux pour delta)
2. Lance les 10 axes (en parallèle ce qui peut l'être : 1+2+5 sur stack frontend+backend+LLM, 4+7 sur data+perf, 6+8 sur sécurité+conformité, 9+10 sur ops)
3. Pour chaque axe : verdict GO/NO-GO + métriques chiffrées
4. Output : `audit_demoema/AUDIT_MINUTIEUX_<date>_<sha>.md` + commentaire Jira sur ticket release
5. Délégation patches : pour chaque NO-GO, recommander le subagent cible (backend/frontend/devops/data/security)

---

## 6. Subagent Claude Code natif `qa-engineer`

Voir `.claude/agents/qa-engineer.md`. Permet d'invoquer ces playbooks via `@qa-engineer audit copilot` ou en délégation depuis la session principale.

Le subagent a accès en lecture/exécution à :
- `Bash` (pour curl, ssh VPS readonly, garak runs)
- `Read`, `Grep`, `Glob` (lecture code)
- MCP `chrome-devtools` (browser audits)
- Playwright MCP (à ajouter sprint QA-3)

Il NE peut PAS : modifier code prod, push, merge, déployer (chain humaine sur écritures critiques).

---

## 7. Échelle de rigueur QA — 5 niveaux progressifs

Le Playbook E (14 axes + 100 % cliquables) place DEMOEMA en **L2 "Audit systématique"**. Pour aller au-delà, voici les disciplines à activer par niveau. Cible long-terme : **L4 "Engineering rigoureux"** (équivalent banques tier-1 / aérospatial light).

### L1 — Tests fonctionnels basiques (avant audit QA round 1)
- pytest happy path uniquement, vitest unit, audits manuels ad-hoc
- Coverage non mesurée, flakiness toléré
- **DEMOEMA état avant 2026-05-01**.

### L2 — Audit systématique (Playbook E actuel ⬅ DEMOEMA aujourd'hui)
- 14 axes minutieux + 100 % éléments cliquables testés
- Coverage line ≥ 70 %, garak red-team hebdo, Schemathesis fuzz
- Métriques chiffrées avant/après chaque release

### L3 — Robustesse + propriétés invariantes (cible Q3 2026)
**+10 disciplines à ajouter** :

1. **Property-based testing systématique** (Hypothesis)
   - Invariants sur scoring : `0 ≤ deal_score ≤ 100`, `tier monotone(CA)`, `EBITDA ≤ CA`, `effectif ≥ 0`
   - `RuleBasedStateMachine` sur le pipeline kanban : chaque transition d'état doit être réversible ou marquée irréversible
   - 1000+ inputs générés par test (vs ~5 cas connus actuellement)

2. **Boundary value testing** systématique
   - Pour chaque seuil business : tester exactement à la frontière (CA = 0, CA = 1€, CA = 1 Md€, CA = float infinity, CA = NaN, CA = -1)
   - Dates : 1900-01-01, 1970-01-01, 2038-01-19 (Unix timestamp overflow), 2100-01-01, dates futures impossibles
   - Chaînes : 0 char, 1 char, 1999 chars, 2000 chars (limite), 2001 chars (over-limit), 1MB string

3. **Negative testing exhaustif**
   - Chaque endpoint : null, tableau vide, type incorrect (str au lieu de int), encoding cassé (latin-1 au lieu UTF-8), SQL injection, XSS, path traversal, command injection
   - Codes erreurs cohérents : 400 vs 422 vs 500 selon classe d'erreur

4. **Fuzzing applicatif** (radamsa, AFL++, atheris pour Python)
   - SIREN, NAF, queries copilot — détecte buffer overflow, regex DoS (ReDoS), unicode tricks
   - 24h de fuzzing par release sur les 10 endpoints les plus exposés

5. **Chaos engineering**
   - Toolkit `litmuschaos` ou simple `tc qdisc` (Linux)
   - Simuler : latency 100-500ms, packet loss 5 %, DB down, DeepSeek timeout, OpenSanctions 503, OOM container
   - Vérifier : dégradation gracieuse (429 plutôt que 5xx), retries OK, fallbacks actifs, alertes émises
   - Quarterly "Game Day" : 1 demi-journée de chaos prod-like

6. **Endurance / soak tests**
   - 24h continu sous charge moyenne (10 VUs) sur staging → memory leaks (RSS stable < +5 %), connection pool stable, MV freshness pas de drift > 1h
   - 7j cron continu pour détecter régressions lentes (DB bloat, log file rotation, secrets expiry, certificat TLS expiry)

7. **Mutation testing** (mutmut Python, Stryker pour TS)
   - Mutmut modifie aléatoirement le code (`+` → `-`, `<` → `>`, `True` → `False`, etc.)
   - Si tests passent malgré mutation → tests faibles
   - **Cible : mutation score ≥ 80 %** sur modules critiques (scoring, copilot, datalake whitelist)
   - Run hebdo, pas par PR (coût élevé)

8. **Differential testing**
   - Comparer 2 implémentations qui devraient être équivalentes :
     - Fiche via SSE copilot vs `/api/datalake/fiche/{siren}` direct → mêmes valeurs canoniques
     - Calcul EBITDA proxy en SQL gold vs en Python backend → delta < 0.01 %
     - Export CSV vs export PDF d'un même deal → mêmes 19 colonnes, mêmes valeurs

9. **Metamorphic testing**
   - Règles métamorphiques (relations entre inputs/outputs sans connaître la valeur exacte) :
     - Si on enrichit une cible avec MORE data, le `deal_score` ne doit JAMAIS baisser (monotonie)
     - Si on traduit une question copilot FR → EN → FR, la réponse doit être sémantiquement équivalente
     - Si on duplique un SIREN dans la query, la réponse doit être identique (idempotence)

10. **Golden datasets / vérité terrain**
    - Corpus annoté manuellement : 50 fiches "vérité terrain" (CA, EBITDA, dirigeants, scoring expert)
    - Test régression : ces 50 fiches doivent toujours produire les mêmes réponses canoniques
    - Mise à jour annuelle (sources INPI changent → re-annoter)

### L4 — Engineering rigoureux (cible 2027)
**+10 disciplines avancées** :

11. **Mutation score ≥ 90 %** sur modules critiques (vs 80 % en L3)

12. **Branch + path coverage** (vs juste line coverage)
    - `pytest --cov-branch` + `Hypothesis` pour générer paths spécifiques
    - **Cible : 90 % branch, 80 % path** sur scoring/auth/copilot

13. **Verification formelle légère** (TLA+ ou Alloy)
    - Spécifier formellement les invariants critiques : auth state machine, transitions kanban, monotonie scoring
    - Modèle TLA+ checké pour ABSENCE de deadlock + safety properties
    - Sortie : preuve mathématique (pas juste tests qui passent)

14. **Contract testing** (Pact, consumer-driven)
    - Frontend déclare son contrat sur backend → backend doit respecter
    - Datalake déclare son contrat avec downstream consumers
    - Brisure de contrat = fail-build automatique

15. **A/B shadow testing** (production silent compare)
    - Déployer 2 versions en parallèle (legacy + new) sur 1 % traffic
    - Comparer outputs en temps réel sans impacter user
    - Détecter régressions subtiles invisibles en staging

16. **Replay & event sourcing testing**
    - Logs structurés tous événements user → replay sur staging
    - Idempotence : rejouer 1000× le même event → state final identique
    - Time-travel : reconstituer le state à n'importe quel moment passé

17. **Tests de fairness / bias**
    - Particulier pour scoring M&A : un dirigeant nom à consonance étrangère (Aïcha, Mamadou, Wei) doit être scoré IDENTIQUEMENT à un nom français équivalent (toutes choses égales par ailleurs)
    - Toolkit : `aif360` (IBM), `fairlearn` (Microsoft) — métriques disparate impact, demographic parity
    - Audit annuel obligatoire (AI Act EU)

18. **LLM judge panel** (vs single judge)
    - 3+ LLMs jugent indépendamment chaque réponse copilot (Prometheus 2 + Claude + GPT-4 ou similaire)
    - Agrégation : majority vote ou moyenne pondérée
    - Détecte position bias, verbosity bias, self-preference bias

19. **SBOM + supply chain attestation**
    - `cyclonedx-bom` génère SBOM par release
    - Sigstore signature des artefacts container
    - SLSA Level 3 attestation provenance build
    - Vérification automatique des deps : pas de package compromis (cf. litellm backdoor 2026-03)

20. **SAST + DAST + IAST combinés**
    - SAST : Bandit (Python), ESLint security, Semgrep custom rules DEMOEMA
    - DAST : OWASP ZAP automatisé sur staging
    - IAST : Contrast Security ou Aikido (open-source) en runtime staging
    - Triangulation des findings → 0 faux positif

### L5 — Continuous quality observability (cible 2028+)
**+10 disciplines top-tier** :

21. **Quality dashboard temps réel** (Grafana)
    - Flake rate, test duration p95, coverage trend, mutation score, hallucination rate copilot live, fail rate par axe Playbook E
    - Alerting si métrique dégrade > seuil

22. **Regression budget**
    - Budget formel : "max 0.1 % régression p95 latency par release"
    - Si dépassé → release bloquée jusqu'à fix

23. **Post-mortem culture stricte**
    - Chaque bug en prod → un nouveau test reproduit le bug AVANT le fix
    - Anti-régression garantie + base de connaissance SCRUM avec catégorisation root-cause

24. **Continuous evaluation prod**
    - Langfuse/Opik trace 100 % des appels LLM → score auto continu (faithfulness, relevance, hallucination)
    - Déclenche audit profond si dégradation > seuil

25. **Visual regression 100 %**
    - Storybook 9 + Chromatic-equivalent OSS (Loki/Playwright snapshots) sur 100 % composants
    - Pixel-diff < 0.1 % vs baseline, 0 régression visuelle non intentionnelle

26. **Tests de récupération désastres**
    - Trimestriel : simulation perte totale datalake → restore from backup en < 4h
    - Tests bascule région (si multi-région un jour) en < 30 min RTO

27. **Bug bounty / red team externe**
    - Programme bug bounty payant (HackerOne / YesWeHack) — bloqué par no_paid_actions sans approbation Zak
    - 1× par an : red team externe (pentest agréé ANSSI) — idem

28. **Fuzzing continu cloud** (OSS-Fuzz style)
    - Cluster dédié 24/7 fuzzing les inputs critiques
    - Coverage-guided + dictionnaire personnalisé (SIREN format, dates FR, NAF codes)

29. **Compliance audits récurrents**
    - RGPD : test droit à l'oubli (DELETE user → vérifier downstream caches/logs/exports purgés)
    - AI Act EU : audit annuel "système IA à risque limité" — transparence, traçabilité, supervision humaine
    - SOC 2 / ISO 27001 si DEMOEMA vise grands comptes

30. **Heuristic evaluation périodique**
    - Audit UX selon 10 heuristiques Nielsen + accessibility WCAG 2.2 par expert externe annuel
    - Comparaison concurrentielle (Mergermarket, PitchBook, Capital IQ) — gap analysis trimestriel

---

### Comment passer L2 → L3 (priorité Q3 2026)

**Quick wins (1 sprint chacun)** :
1. **Hypothesis sur scoring** (1 j) → property-based testing sur `compute_deal_score`, `compute_tier`, `extract_dirigeants_from_text`
2. **Boundary tests SIREN/NAF/dates** (1 j) → cas limites systématiques
3. **Golden dataset 50 fiches** (3 j) → annotation manuelle + corpus versionné `backend/tests/fixtures/golden_50.json`
4. **mutmut sur 5 modules critiques** (2 j) → mutation score baseline + cible 80 %
5. **Differential SSE vs REST** (1 j) → assertion CA/EBITDA identiques entre les 2 chemins

**Effort important** :
6. **Chaos engineering quarterly Game Day** (5 j initial + 0.5 j/q) → toolkit + 1ère exécution
7. **Endurance 24h soak test** (3 j initial + cron) → CI nightly extended
8. **Negative testing exhaustif** (5 j) → décliner les 10 endpoints critiques avec ~50 negative cases each

**Mesures à dashboard immédiat** :
- `mutation_score` : objectif → 80 % L3, 90 % L4
- `branch_coverage` : objectif → 80 % L3, 90 % L4
- `flake_rate` : objectif → < 1 % L3, < 0.1 % L4
- `MTTR_audit_to_patch` : objectif → < 24h L3, < 4h L4

### COUVERTURE MAXIMALE — 15 dimensions de coverage

La rigueur QA exige de mesurer **toutes** les dimensions de couverture, pas juste line coverage. Une suite "à 95 % ligne" peut avoir 30 % branch et 0 % mutation = passoire. Voici les 15 dimensions à dashboarder, chacune avec commande et seuils par niveau.

| # | Dimension | Outil | Seuil L2 | Seuil L3 | Seuil L4 | Seuil L5 | Commande mesure |
|---|---|---|---|---|---|---|---|
| 1 | **Line coverage** | `pytest --cov=backend` + `vitest --coverage` | 70 % | 85 % | 95 % | 98 % | `pytest --cov=backend --cov-fail-under=95 --cov-report=html` |
| 2 | **Branch coverage** | `pytest --cov-branch` | 60 % | 80 % | 90 % | 95 % | `pytest --cov-branch --cov-report=term-missing` |
| 3 | **Path coverage** | `coverage.py` paths + Hypothesis | non mesuré | 70 % | 80 % | 90 % | `coverage report --show-missing --include="backend/*"` |
| 4 | **Mutation coverage** | `mutmut` (Python), `Stryker` (TS) | non mesuré | 80 % | 90 % | 95 % | `mutmut run --paths-to-mutate=backend/clients/deepseek.py` |
| 5 | **API endpoint coverage** | Schemathesis stateful + OpenAPI introspection | 100 % path | 100 % path × 5 méthodes | 100 % × tous query params | 100 % × params × auth scopes | `st fuzz https://api/openapi.json --report=allure-results` |
| 6 | **Clickable coverage** | Playwright auto-discovery (cf. §5 axe 1.bis) | 100 % visibles | 100 % × 3 breakpoints | 100 % × 3 BP × 3 themes × 2 connectivity | 100 % × matrice complète | `playwright test clickables-exhaustive.spec.ts` |
| 7 | **LLM tool coverage** | DeepEval `ToolCorrectness` sur les 16 tools | 100 % tools individuels | 100 % × parallel calls | 100 % × multi-turn × 3 ordres | 100 % × pass^k=3 | `deepeval test run backend/tests/eval/tool_correctness.py` |
| 8 | **Data quality coverage** | Soda Core scans toutes tables `silver.*`+`gold.*` | 80 % tables | 100 % tables × not_null | 100 % tables × 5 checks (null, unique, range, regex, fk) | 100 % × drift detection whylogs | `soda scan -d demoema -c configuration.yml checks.yml` |
| 9 | **Visual regression coverage** | Storybook 9 + Playwright `toHaveScreenshot()` | 30 % composants | 70 % | 100 % composants `dem/*` | 100 % × 4 themes × 3 breakpoints | `playwright test visual --update-snapshots` |
| 10 | **Browser coverage** | Playwright cross-browser | 1 (Chromium) | 2 (Chrome+Firefox) | 4 (Chromium, Firefox, WebKit, MS Edge) | 4 × matrix versions (3 derniers majeurs) | `playwright test --project=chromium,firefox,webkit,msedge` |
| 11 | **Device / responsive coverage** | Playwright `device` emulation + Lighthouse mobile | desktop 1080p | + iPhone 15 + Pixel 8 | + iPad + desktop 4K + ultrawide (6 devices) | + folding + watch (8 devices) | `playwright test --project=mobile,tablet,desktop` |
| 12 | **Locale coverage** | Tests payloads multilingues + accents | FR ASCII | FR + accents éà ç | FR + EN + CJK + RTL ar/he | + emoji 4-byte + NFC/NFD | `pytest backend/tests/test_i18n_payloads.py` |
| 13 | **Persona / role coverage** | Tests par rôle utilisateur | 1 (admin) | 2 (admin, analyst) | 3 (admin, analyst, viewer) | 5 (+ guest, super-admin) | `pytest -m "role_admin or role_analyst" backend/tests/` |
| 14 | **State coverage** (matrice combinaisons) | Tests par combinaison d'états | 1 state | 4 (logged in/out × empty/full data) | 16 (+ online/offline × dark/light) | 64 (+ persona × locale × device) | matrix dans `playwright.config.ts` |
| 15 | **Negative test coverage** | Pour chaque happy path, N tests négatifs | 1 négatif / 1 happy | 3 / 1 | 5 / 1 | 10 / 1 | `pytest -m "negative" --collect-only \| wc -l` |

#### Commandes "audit couverture maximale" à lancer en CI nightly

```bash
# Backend Python — coverage maximale
pytest backend/tests/ \
  --cov=backend \
  --cov-branch \
  --cov-report=term-missing \
  --cov-report=html:htmlcov \
  --cov-report=xml \
  --cov-fail-under=95 \
  --hypothesis-show-statistics \
  -m "not slow"

# Mutation testing weekly (long, lance dimanche)
mutmut run --paths-to-mutate=backend/clients/deepseek.py,backend/main.py
mutmut results
mutmut html

# Frontend — vitest coverage + Playwright clickables
cd frontend
pnpm vitest run --coverage --coverage.thresholds.lines=85 \
  --coverage.thresholds.branches=80 --coverage.thresholds.functions=85
pnpm playwright test --project=chromium,firefox,webkit,msedge \
  clickables-exhaustive.spec.ts visual.spec.ts

# API contract fuzz (Schemathesis stateful)
st fuzz https://82-165-57-191.sslip.io/openapi.json \
  --auth-type=bearer --hypothesis-deadline=600000 \
  --report=allure-results

# LLM eval (DeepEval)
deepeval test run backend/tests/eval/

# Data quality (Soda Core)
soda scan -d demoema_prod -c qa/soda/configuration.yml qa/soda/checks/

# Visual regression (Playwright snapshots)
pnpm playwright test visual --reporter=html

# A11y (axe-core sur 14 routes)
pnpm playwright test a11y --reporter=html

# Bundle / dead code
pnpm size-limit
pnpm knip --reporter=compact
```

#### Dashboard "Quality Coverage 15D" (Grafana à construire)

Une page Grafana avec 15 jauges (une par dimension), seuils par couleur :
- 🟢 Vert : ≥ seuil L4
- 🟡 Jaune : ≥ seuil L3
- 🟠 Orange : ≥ seuil L2
- 🔴 Rouge : < L2 (régression critique)

Trend hebdo : courbe par dimension sur 12 semaines glissantes. Alerte Slack si une dimension passe rouge.

#### Métriques agrégées long-terme

- **Quality Coverage Score (QCS)** : moyenne pondérée des 15 dimensions normalisées 0-100. Cible L3 = 80, L4 = 90, L5 = 95.
- **Test Pyramid Health** : ratio unit / integration / E2E doit être 70/20/10 (pas inversé)
- **CI Time vs Coverage** : courbe coût/bénéfice — si CI > 30 min, paralléliser ou skip slow tests sur PRs non-prod
- **Flake Rate par dimension** : aucune dimension ne doit dépasser 1 % flake (un flake = vrai bug à fixer)
- **Coverage Velocity** : Δ coverage par sprint — doit augmenter de 1-2 pp jusqu'à atteindre cible L4

#### Outils OSS pour le dashboard quality

- **Codecov** ou **Coveralls** (gratuit pour repos publics, payant privés) — ou **alternative OSS auto-hébergée** : `codecov-action` GitHub stocke en repo
- **dorny/test-reporter** GitHub Action — agrège jUnit/pytest XML
- **Allure Report** — rapport HTML interactif Schemathesis + Playwright
- **mutmut** results en HTML hosté GitHub Pages
- **Storybook 9 test runner report** — visual regression diff dans PR

### Anti-pattern : la rigueur n'est PAS le volume

⚠️ Avoir 10 000 tests qui passent ≠ tests rigoureux. Signes d'une suite faible :
- Tests qui ne fail jamais (mutation score < 50 %)
- Coverage gonflée par tests `assert True`
- Snapshots aveugles ("le test passe parce qu'on a regénéré la golden snapshot")
- Tests dépendant les uns des autres (ordre d'exécution matters)
- "Skip if flaky" — vrai flakiness = vrai bug à fixer
- Tests qui se contentent de "ne pas crasher" sans assertion sur la valeur retournée
- Pas de tests négatifs (que des happy paths)
- Tests qui re-testent ce que le framework garantit déjà (FastAPI valide pydantic, pas besoin de re-tester ça)

**Règle** : un test rigoureux fail si on casse INTENTIONNELLEMENT le code qu'il vérifie. Sinon il est inutile.

---

## 8. Plan d'adoption L2 → L4 — 12 semaines (2026-05-02 → 2026-07-25)

**Décision stratégique (2026-05-02)** : DEMOEMA cible **L4 minimum** pour la prod payante. Pas de release majeure investisseur sans QCS ≥ 90 sur les 15 dimensions.

**Effort estimé** : ~8-10 ingénieur-semaines réparties sur 6 sprints de 2 semaines (~1.5-2 dévs full-time, ou 3-4 dévs à 50 % focus QA).

**Coût** : 0 € (tous outils OSS — Hypothesis, mutmut, Schemathesis, DeepEval, Soda Core, Pact, axe-core, Bandit, Semgrep, OWASP ZAP, TLA+, litmuschaos, etc.). Aucun SaaS payant sans approbation explicite Zak.

### Sprint 1 (semaine 1-2 : 2026-05-04 → 2026-05-15) — Quick wins L3 fondations

| Ticket | Discipline | Effort | Output |
|---|---|---|---|
| `qa-l4-01` | Hypothesis property-based scoring M&A | 2 j | `backend/tests/properties/test_scoring_invariants.py` (10+ propriétés) |
| `qa-l4-02` | Boundary value tests SIREN/NAF/dates/CA | 1 j | `backend/tests/test_boundary_values.py` |
| `qa-l4-03` | Golden dataset 50 fiches vérité terrain | 3 j | `backend/tests/fixtures/golden_50.json` annoté manuellement |

**Verdict sprint 1** : `pytest -m "property or boundary or golden"` green + Hypothesis stats > 1000 inputs/test.

### Sprint 2 (semaine 3-4 : 2026-05-18 → 2026-05-29) — Mutation + Differential

| Ticket | Discipline | Effort | Output |
|---|---|---|---|
| `qa-l4-04` | mutmut baseline scoring/copilot/datalake | 2 j | mutation score baseline measured ; cible 80 % |
| `qa-l4-05` | Differential SSE vs REST vs CSV vs PDF | 1 j | `backend/tests/test_differential_paths.py` |
| `qa-l4-06` | Metamorphic tests (monotonie/idempotence) | 2 j | `backend/tests/properties/test_metamorphic.py` |

**Verdict sprint 2** : mutation score ≥ 80 % sur 5 modules critiques (`backend/clients/deepseek.py`, `backend/main.py::copilot_*`, `backend/datalake.py::scoring*`, `backend/main.py::_PROMPT_INJECTION_PATTERNS`, `backend/routers/datalake.py::_fiche_entreprise_uncached`).

### Sprint 3 (semaine 5-6 : 2026-06-01 → 2026-06-12) — Chaos + Endurance + Negative

| Ticket | Discipline | Effort | Output |
|---|---|---|---|
| `qa-l4-07` | Chaos engineering Game Day | 3 j | `qa/chaos/litmuschaos-experiments.yaml` + 1ère exécution |
| `qa-l4-08` | Endurance 24h + cron 7j | 2 j | GitHub Actions workflow `endurance.yml` + Grafana dashboard |
| `qa-l4-09` | Negative testing exhaustif | 3 j | 50 cas négatifs / 10 endpoints critiques (≥ 500 tests) |
| `qa-l4-10` | Fuzzing radamsa/atheris | 2 j | corpus fuzz + 24h CI cluster nightly |

**Verdict sprint 3** : Game Day OK (système dégrade gracieusement, RTO < 15 min) + 0 OOM endurance + 0 vulnérabilité fuzz critique.

### Sprint 4 (semaine 7-8 : 2026-06-15 → 2026-06-26) — Contracts + Fairness + Judge panel

| Ticket | Discipline | Effort | Output |
|---|---|---|---|
| `qa-l4-11` | Contract testing Pact | 2 j | broker Pact local + 3 contrats (frontend↔backend↔datalake) |
| `qa-l4-12` | Tests fairness/bias scoring | 2 j | `backend/tests/test_fairness.py` (aif360 ou fairlearn) |
| `qa-l4-13` | LLM judge panel 3+ judges | 3 j | `backend/tests/eval/judge_panel.py` (Prometheus 2 OSS + 2 autres) |
| `qa-l4-14` | Replay & event sourcing | 2 j | logs structurés JSON + replay harness staging |

**Verdict sprint 4** : Contracts Pact green + 0 bias détecté (disparate impact < 0.8) + judge panel agree ≥ 80 % sur 100 réponses.

### Sprint 5 (semaine 9-10 : 2026-06-29 → 2026-07-10) — Verification + Supply chain + SAST/DAST

| Ticket | Discipline | Effort | Output |
|---|---|---|---|
| `qa-l4-15` | Verification formelle TLA+ légère | 3 j | `qa/tla/auth_state_machine.tla` + `qa/tla/scoring_monotone.tla` checked OK |
| `qa-l4-16` | SBOM + sigstore + SLSA L3 | 2 j | CI génère SBOM par release + signature artefacts |
| `qa-l4-17` | SAST + DAST + IAST | 3 j | Bandit + Semgrep + OWASP ZAP staging + alerting findings |
| `qa-l4-18` | A/B shadow 1 % prod | 2 j | proxy nginx/caddy split traffic + diff log |

**Verdict sprint 5** : TLA+ no deadlock + 0 finding SAST/DAST high+ + SBOM signé chaque release.

### Sprint 6 (semaine 11-12 : 2026-07-13 → 2026-07-24) — Dashboard QCS + audit final L4

| Ticket | Discipline | Effort | Output |
|---|---|---|---|
| `qa-l4-19` | Dashboard Grafana 15D + alerting | 3 j | dashboard JSON déployé + 15 alertes Slack |
| `qa-l4-20` | Migration L4 finale + audit complet | 5 j | rapport `audit_demoema/AUDIT_L4_FINAL.md` + QCS ≥ 90 |

**Verdict sprint 6** : QCS ≥ 90 calculé en automatique + tableau de bord live + audit complet 14 axes 100 % GO.

### Métriques de progression hebdomadaires

Chaque semaine, le qa-engineer subagent émet un rapport Slack auto avec :
- **QCS courant** (0-100, baseline L2 ≈ 55, cible L4 = 90)
- **Tickets QA L4** : open / in-progress / done sur les 20
- **Coverage par dimension** : line %, branch %, mutation %, etc.
- **Régressions vs baseline** : alerte si une dimension baisse > 5 pp
- **CI time** : doit rester < 30 min (paralléliser si dépasse)

### Risques & mitigations

| Risque | Impact | Mitigation |
|---|---|---|
| Chaos Game Day révèle bugs critiques imprévus | sprint 3 retardé | Buffer 1 semaine sprint 3 ; prioriser fixes critiques avant continuer |
| TLA+ courbe d'apprentissage | sprint 5 retardé | Réduire scope à 1 invariant (auth state) plutôt que 3 |
| Mutation score < 80 % nécessite refactor majeur | sprint 2 retardé | Accepter 70 % temporairement, ticket dette tech pour Q4 |
| LLM judges disagreement persistent | métrique faithfulness instable | Augmenter panel à 5 judges + références obligatoires |
| Hypothesis trouve crash bugs nouveaux | sprint 1 dérive | Boucle short-fix : nouveau bug = nouveau ticket SCRUM, pas blocage sprint |

### Critères GO production payante (post-sprint 6)

- ✅ QCS ≥ 90 calculé en automatique
- ✅ 14 axes Playbook E tous GO
- ✅ 350-400+ éléments cliquables 100 % testés (axe 1.bis)
- ✅ Mutation score ≥ 90 % sur les 5 modules critiques
- ✅ 0 finding SAST/DAST high+
- ✅ TLA+ vérification formelle invariants critiques OK
- ✅ Bias / fairness audit OK (disparate impact < 0.8)
- ✅ Chaos Game Day passé (RTO < 15 min)
- ✅ Endurance 24h + 7j sans memory leak / MV drift
- ✅ Dashboard Grafana 15D vert sur toutes dimensions

Sans ces 10 critères → la release n'est pas prod-grade et reste en staging/beta.

---

## 9. Dimensions complémentaires à activer (au-delà L4)

Audit retrospectif des 14 axes existants → 10 dimensions critiques **non encore couvertes** identifiées. Priorisation pour L4+ (must-have avant prod payante) ou L5 (nice-to-have).

### Dimension 15 — Architecture & qualité code statique (must-have L4)
- **Complexité cyclomatique** : `radon cc backend/ --average` → cible avg < 5, max < 15 par fonction
- **Maintainability Index** : `radon mi backend/` → cible > 70 sur tous modules
- **Dead code** : `vulture` Python + `knip` JS/TS → 0 fonction/import unused
- **Dépendances circulaires** : `madge --circular frontend/src/` + `tach` Python boundaries → 0 cycle
- **SonarQube-équivalent OSS** : `pylint`, `mypy --strict`, `eslint --max-warnings=0`
- **Couplage / cohésion** : analyse `dependency-cruiser` JS/TS → règles boundaries (frontend/components ne peut pas importer backend/*)
- **Code smells** : duplication > 5 % via `jscpd` ou `pmd-cpd` → fail-build
- **Architecture fitness functions** : tests qui échouent si l'archi viole une règle (ex: `backend/datalake.py::GOLD_TABLES_WHITELIST` doit être source-of-truth, pas dupliqué)
- **Verdict** : pass si CC avg < 5 + MI > 70 + 0 dead code + 0 circular dep + ESLint/Pylint 0 warnings

### Dimension 16 — Audit trail métier M&A (must-have L4 — deal confidentiality)
DEMOEMA traite des **deals confidentiels** — qui a vu quelle fiche, quand, depuis où ? Critique pour secret affaires + RGPD + futur audits clients.
- **Table `silver_qa.audit_log`** : chaque accès à une fiche cible logué (user_id, siren_consulté, endpoint, timestamp, ip_hash, user_agent_hash)
- **Retention 90 j minimum** (extensible 5 ans pour compliance investisseurs)
- **Endpoint admin `/api/admin/audit?user_id=X&from=...&to=...`** : qui a vu quoi (réservé super-admin)
- **Endpoint utilisateur `/api/me/access-log`** : RGPD art. 15 — l'utilisateur dirigeant a droit de savoir qui a consulté sa fiche
- **Alerting suspicious patterns** : > 100 fiches consultées par 1 user en < 1h → flag suspect (scraping/leak)
- **Pas de PII en clair dans audit log** : seulement IDs et hash
- **Verdict** : pass si chaque consultation tracée + retention 90j + endpoint admin testé + alerting actif

### Dimension 17 — Time/Calendar correctness (must-have L4)
- **DST changes** : test queries chevauchant 2026-03-29 02h (FR DST forward) et 2026-10-25 03h (DST back) → pas de duplication ni perte d'heure
- **Fuseau horaire** : tous timestamps en `timestamptz` UTC en DB, conversion `Europe/Paris` à l'affichage uniquement
- **Leap year** : test `compute_age('1996-02-29')` au 2024-02-29 → 28 ans (pas crash)
- **Leap second** : si DEMOEMA touche aux microsecondes, vérifier comportement DB Postgres
- **Date impossibles** : `2026-02-30` rejeté en 422, pas crash 500
- **Date futures** : SIRENE date_creation = '2050-01-01' → flag ou rejet (pas accepté silencieusement)
- **Chevauchement minuit** : query `freshness < 24h` à 23h59 ne doit pas exclure des rows enregistrées à 23h58
- **Test Hypothesis** : `from hypothesis.strategies import datetimes` → générer 1000+ dates incluant edge cases
- **Verdict** : pass si test_temporal.py couvre 7 cas + 0 crash sur dates impossibles

### Dimension 18 — Précision numérique (must-have L4 — calculs financiers)
- **Postgres** : montants en `numeric(18,2)`, jamais `float`/`real`/`double precision`
- **Python** : utiliser `decimal.Decimal` pour calculs M&A, pas `float`
- **JavaScript** : `Number` est IEEE 754 → précision limitée. Utiliser `decimal.js` ou string pour montants
- **Test invariant** : `(a + b) - b == a` doit être vrai pour CA/EBITDA (vérifier avec Hypothesis 1000 inputs)
- **Arrondi banking** : `ROUND_HALF_EVEN` (banker's rounding) pas `ROUND_HALF_UP` pour éviter biais cumulatif
- **Affichage cohérent** : `formatEur(204531122.45)` → "204,5 M€" partout (cf. G8 helper)
- **Pas d'overflow** : CA cap 1e12 (1 trillion) pour éviter overflow numérique
- **Comparaison floats** : jamais `==`, toujours `pytest.approx(rel=1e-6)`
- **Verdict** : pass si 0 `float` pour montants + arrondi banking + 100 % invariants Hypothesis

### Dimension 19 — Concurrency conflicts (must-have L4)
- **Optimistic locking** : ajouter `version` ou `updated_at` colonne, ETag header, comparaison à update
- **Pessimistic locking** : `SELECT ... FOR UPDATE` pour transactions critiques (ex: assignment cible analyste)
- **Isolation level Postgres** : par défaut `READ COMMITTED`, élever à `SERIALIZABLE` pour transactions financières
- **Test write-write conflict** : 2 users updatent la même fiche cible → 1 succès + 1 retry/error explicite
- **Test stale read** : user A lit fiche, user B update, user A submit avec version old → 409 Conflict
- **Last-write-wins documenté** : pour les champs où c'est OK (ex: notes textuelles), pas pour scoring/financial
- **Idempotence keys** : POST endpoints critiques acceptent `Idempotency-Key` header (cf. Stripe pattern)
- **Verdict** : pass si optimistic locking sur 5 endpoints critiques + 409 testé + Idempotency-Key supporté

### Dimension 20 — DX agentic / LLM-friendly API (must-have L4)
DEMOEMA expose API → utilisable par d'autres LLMs (Claude, GPT-4, agents internes Cursor). Doit être agentic-ready.
- **OpenAPI rich** : chaque endpoint a `summary`, `description`, `examples`, `responses` complets (pas juste 200)
- **Tool descriptions claires** : pour les 16 tools du copilot DeepSeek, descriptions explicites en FR + EN
- **Erreurs LLM-friendly** : message d'erreur explicite + suggestion (`"SIREN invalide. Format attendu: 9 chiffres consécutifs. Exemple: 333275774"`)
- **Pagination cohérente** : `limit`/`offset` ou cursor `?after=...`, jamais incohérence entre endpoints
- **Field naming consistent** : `siren` partout (pas `siren_id` ici, `idSiren` là), `created_at` (pas `creation_date` ou `date_creation`)
- **Idempotence claire** : doc indique GET = idempotent, POST = pas, etc.
- **Test "Claude peut utiliser DEMOEMA via tool calls"** : feed l'OpenAPI à Claude → demander "fais-moi une fiche EQUANS" → Claude tool-calls correctement
- **MCP server natif** : exposer DEMOEMA en serveur MCP pour intégration directe dans Claude Code/Cursor
- **Verdict** : pass si Claude eval test green + OpenAPI 100 % examples + erreurs LLM-friendly

### Dimension 21 — Crisis communication & status page (must-have L4)
- **Status page publique** : Cachet (OSS, auto-hébergé) ou Statping → `status.demoema.fr`
- **Composants exposés** : Frontend, API, Datalake, Copilot LLM, Workers ingestion
- **Incidents publiés** : auto-publication depuis Prometheus alerting (déclenchement > 5 min)
- **Templates communication** : email user "service partiellement dégradé", "incident résolu", "post-mortem"
- **Post-mortem public** : pour incidents > 1h, post-mortem publié sous 7j (root cause, timeline, action items)
- **RSS/Webhook** : status updates en RSS pour intégration Slack interne + customers
- **Test drill** : trimestriel, simuler incident → status page mis à jour < 5 min, post-mortem rédigé < 7j
- **Verdict** : pass si status page live + 1 drill réalisé + 1 post-mortem publié

### Dimension 22 — Vendor risk + exit plan (must-have L4)
DEMOEMA dépend de : DeepSeek (LLM), Hetzner (VPS staging), IONOS (VPS prod), Cloudflare (CDN), Atlassian (Jira/Confluence), GitHub (repo+CI). Chacun = single point of failure.
- **DeepSeek** : si abandonné/banni → fallback Claude API (Anthropic) ou Mistral. Test mensuel switch provider via env `LLM_PROVIDER=anthropic`
- **IONOS VPS** : si down 24h+ → restore datalake sur Hetzner backup. Test annuel restore.
- **Cloudflare** : si compte banni → fallback Vercel CDN. DNS séparé (Gandi) pour switch < 1h
- **Atlassian** : si tombé → backup Jira mensuel JSON dans repo. Possibilité migration vers Linear/Notion
- **GitHub** : si banni → mirror GitLab self-hosted. Backup repo quotidien
- **Vendor SLA tracking** : table `vendor_sla` avec uptime promised vs réel mensuel
- **Exit plan documenté** : `docs/VENDOR_EXIT_PLANS.md` avec procédure pour chaque vendor critique
- **Test annuel switch** : 1 vendor/an testé en switch live (DeepSeek → Claude → DeepSeek)
- **Verdict** : pass si exit plans documentés + 1 switch testé/an + DNS séparé du CDN

### Dimension 23 — Test pyramid health monitoring (nice-to-have L5)
- **Ratio idéal** : 70 % unit / 20 % integration / 10 % E2E
- **Mesure mensuelle** : count par catégorie via tags pytest/Playwright
- **Alerte** : si E2E > 20 % du total → suite va devenir lente + flaky
- **Alerte** : si unit < 60 % → manque tests fondamentaux
- **CI time budget** : suite complète < 30 min ; si dépasse → paralléliser ou skip slow PRs non-prod
- **Flake rate par catégorie** : E2E < 1 %, integration < 0.5 %, unit < 0.1 %

### Dimension 24 — Knowledge management & onboarding (nice-to-have L5)
- **ADR (Architecture Decision Records)** : `docs/adr/NNNN_<title>.md` pour décisions architecturales (déjà partiellement fait avec `docs/DECISIONS_VALIDEES.md`)
- **Runbooks ops** : 1 runbook par scénario (incident, deploy, rollback, restore, scale-up)
- **Onboarding new dev** : checklist + script auto qui setup env local en 1 commande (`make dev-setup`) + tutorial 30 min
- **Vidéos training** : enregistrer screencast 5-10 min par feature majeure (copilot, datalake, scoring)
- **Atelier internal QA L4** : formation 2j à l'équipe sur les playbooks A-F + outils (Hypothesis, Schemathesis, Playwright, garak)

### Dimension 25 — License compliance & SBOM continu (nice-to-have L5)
- **Inventaire deps** : `pip-licenses` Python + `license-checker` JS → toutes deps avec licence
- **Pas de GPL/AGPL** dans le runtime (incompatible code propriétaire DEMOEMA)
- **SBOM** : `cyclonedx-bom` génère SBOM par release, hosté GitHub release artifacts
- **Renovate / Dependabot** : auto-PR mensuelles pour deps mineures, manuel pour majors
- **Audit license annuel** : grep tous les `LICENSE` en deps pour compliance

---

### Synthèse priorisation L4

Pour atteindre L4 prod-grade payante (cible 2026-07-25), activer les **8 dimensions must-have** :

| Dim | Priorité | Effort | Sprint cible |
|---|---|---|---|
| 15 Architecture statique | Must-have L4 | 2 j | S5 (existing slot) |
| 16 Audit trail métier | Must-have L4 (RGPD + secret M&A) | 3 j | S4 |
| 17 Time/Calendar | Must-have L4 | 2 j | S2 (avec Hypothesis) |
| 18 Précision numérique | Must-have L4 | 2 j | S2 |
| 19 Concurrency conflicts | Must-have L4 | 3 j | S5 |
| 20 DX agentic | Must-have L4 | 3 j | S6 |
| 21 Crisis communication | Must-have L4 | 3 j | S6 |
| 22 Vendor exit plans | Must-have L4 | 2 j | S5 |

**+20 jours-homme** ajoutés au plan 12 semaines = ~66 j-h total = 11-13 ingénieur-semaines (vs 8-10 estimé initial). Réviser planning : ajouter 2 semaines (sprint 7) ou paralléliser 4 dévs sur 12 semaines.

**Tickets SCRUM-157 → SCRUM-164** à créer pour ces 8 dimensions (j'ai créé 1 epic + 20 stories = SCRUM-136 → SCRUM-156, prochain serait 157).

---

## 10. Sources état de l'art (référencées 2026-05-02)

### Anthropic / Claude Code
- [Subagents docs](https://code.claude.com/docs/en/sub-agents)
- [Skills docs](https://code.claude.com/docs/en/skills.md)
- [MCP servers](https://code.claude.com/docs/en/mcp-servers.md)
- [SHADE-Arena red-teaming](https://alignment.anthropic.com/2025/strengthening-red-teams/)

### Frameworks LLM-QA
- [DeepEval](https://github.com/confident-ai/deepeval) (15.1k★, v3.9.9 — 2025-12)
- [DeepTeam OWASP_ASI_2026](https://github.com/confident-ai/deepteam) (1.6k★, v1.0.4)
- [Promptfoo](https://github.com/promptfoo/promptfoo) (20.8k★, v0.121.9 — 2026-04)
- [NVIDIA garak](https://github.com/NVIDIA/garak) (7.7k★, v0.15.0 — 2026-05)
- [Microsoft PyRIT](https://github.com/microsoft/PyRIT) (3.8k★, v0.13)
- [Schemathesis](https://github.com/schemathesis/schemathesis) (3.3k★, 2026-04)
- [browser-use](https://github.com/browser-use/browser-use) (91.7k★, v0.12.6)
- [Stagehand](https://github.com/browserbase/stagehand) (22.4k★, 2026 actif)

### Papers académiques 2024-2026
- [τ²-bench Sierra Research](https://arxiv.org/pdf/2506.07982) — pass^k robustesse multi-essais
- [AIRTBench](https://arxiv.org/html/2506.14682v1) — autonomie red-teaming
- [HalluLens ACL 2025](https://arxiv.org/html/2504.17550v1) — hallucination dynamique
- [Prometheus 2](https://arxiv.org/abs/2405.01535) — LLM-judge open-source
- [Judging the Judges ACL 2025](https://arxiv.org/abs/2406.07791) — biais LLM-as-judge
- [BFCL Berkeley](https://gorilla.cs.berkeley.edu/leaderboard.html) — tool-calling benchmark
- [LiveBench](https://arxiv.org/abs/2406.19314) — anti-contamination test set

### Patterns prod
- [OpenObserve Council of Sub Agents](https://openobserve.ai/blog/autonomous-qa-testing-ai-agents-claude-code/) — 380→700 tests, flakes -85%
- [agents.md spec GitHub](https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/)
- [Greptile vs CodeRabbit benchmarks](https://www.greptile.com/benchmarks)
