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

### Playbook D — Audit datalake gold/silver intégrité (cycle mensuel)

**Quand le déclencher** : après chargement majeur de source (>100k rows ingérées), changement schema gold, ou mise en prod nouvelle MV.

**Pré-requis** :
- SSH VPS : `ssh -i ~/.ssh/demoema_ionos_ed25519 root@82.165.57.191`
- ou endpoint `/api/datalake/_introspect`

**Vérifications canoniques** :
```sql
-- Gap silver→gold (cibles silver pas dans gold)
SELECT COUNT(*) AS silver_not_in_gold
FROM silver.inpi_comptes c
WHERE NOT EXISTS (SELECT 1 FROM gold.entreprises_master m WHERE m.siren=c.siren);
-- Cible : < 1% du count silver

-- Cohérence dashboard ↔ fiche (CA même valeur)
SELECT em.siren, em.ca_dernier AS gold_ca, sc.ca AS silver_ca
FROM gold.entreprises_master em
JOIN silver.inpi_comptes sc ON sc.siren = em.siren
WHERE ABS(em.ca_dernier - sc.ca) / NULLIF(sc.ca,0) > 0.01
LIMIT 50;
-- Cible : 0 row (tolérance < 1%)

-- Tables gold whitelisted ont au moins 1 row
SELECT t, GREATEST(0, reltuples::bigint) AS rows
FROM pg_class
JOIN pg_namespace n ON n.oid = relnamespace
WHERE n.nspname = 'gold' AND t IN (
  -- liste GOLD_TABLES_WHITELIST de backend/datalake.py
)
AND reltuples = 0;
-- Cible : 0 row
```

**Index/MV à maintenir** :
```sql
-- Index manquants identifiés (SCRUM-133)
CREATE INDEX IF NOT EXISTS press_mentions_siren_idx
  ON gold.press_mentions(siren);
REFRESH MATERIALIZED VIEW CONCURRENTLY gold.sanctions_master;
```

**Métriques de freshness** : `silver.<table>.ingested_at` doit être < 24h pour les sources quotidiennes (BODACC, INPI), < 7 j pour mensuelles (HATVP, OFAC).

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

**Verdict axe 1** : pass uniquement si Lighthouse perf > 80, a11y > 95, SW registered, 0 console error, **ET 100 % des éléments cliquables PASS dans clickables-exhaustive.spec.ts** (350-400+ éléments distincts sur les 14 routes).

### Axe 2 — Backend API (FastAPI / SSE / contracts)
- **OpenAPI fuzz** : Schemathesis sur `/openapi.json` (couvre tous les endpoints en 1 commande)
- **Pytest coverage** : objectif 70 % global, 90 % sur modules critiques (auth, scoring, copilot)
- **Latency profiling** : k6 ou Locust sur top endpoints (`/api/datalake/dashboard`, `/api/datalake/fiche/{siren}`, `/api/copilot/stream`)
- **SSE streaming** : test stream 30-90 s sans reconnect ou perte d'event `done:true`
- **Error handling** : 401, 403, 422, 429, 500 cohérents — schema d'erreur unifié
- **Verdict** : pass si Schemathesis 0 schema violation, p95 endpoint top-10 < SLA, coverage seuil OK

### Axe 3 — Logique métier (scoring M&A / matching / business rules)
- **Property-based testing** : Hypothesis sur invariants `deal_score ∈ [0,100]`, `tier monotone(CA)`, `EBITDA ≤ CA`
- **Decision tables** : règles scoring documentées en CSV testable (decisiontable Python)
- **Matching dirigeants fuzzy** : `recordlinkage` sur sample annoté (Pinault/PINAULT/pinault → même entité)
- **Entity resolution** : doublons SIREN détectés sur `silver.inpi_dirigeants`
- **Calculs financiers** : EBITDA proxy = CA × (1 - charges_perso_taux × ...). Test vs golden dataset 50 entreprises
- **Verdict** : pass si 100 % invariants Hypothesis green + 0 doublon SIREN/entité

### Axe 4 — Données (silver/gold quality + lineage + freshness)
- **Great Expectations / Soda Core** : checkpoints sur `silver.*` + `gold.*` (not_null, unique, range, regex pattern)
- **Freshness** : `silver.<table>.ingested_at` < 24 h pour quotidiens (BODACC, INPI), < 7 j pour mensuels
- **Drift detection** : whylogs ou ydata-profiling baseline → alerte si distribution col change > seuil
- **Gap silver→gold** : `SELECT COUNT(*) FROM silver.X WHERE NOT EXISTS gold.X` < 1 %
- **Cohérence dashboard↔fiche** : delta CA < 1 % sur 100 SIREN sample
- **MV refresh** : `pg_stat_user_tables.last_analyze < 24 h` sur les MV gold critiques
- **Verdict** : pass si 100 % checkpoints GE green + 0 gap > 1 % + freshness OK

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

## 7. Sources état de l'art (référencées 2026-05-02)

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
