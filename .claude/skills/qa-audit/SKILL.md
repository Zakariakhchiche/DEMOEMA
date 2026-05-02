---
name: qa-audit
version: 2.1.0
description: Lance un audit QA DEMOEMA selon un des 5 playbooks (A/B/C/D/E) ou un sous-axe ciblé. Use when l'utilisateur demande "lance un audit", "teste tout", "audit copilot", "audit security", "audit datalake", "audit nav", "audit clickables", "audit browser", "audit backend", "audit minutieux", "audit l4", "audit régression", ou veut vérifier l'état QA avant une release. Le skill délègue au subagent qa-engineer après avoir résolu le scope.
allowed-tools: [Read, Bash, Grep, Glob, Agent, TaskCreate, TaskUpdate, WebFetch, WebSearch, mcp__chrome-devtools__*]
---

# QA Audit DEMOEMA — Skill orchestrateur (v2.1.0, 2026-05-02)

## Changelog v2.0.0 → v2.1.0 (audit régression a révélé 5 gaps)

1. **Smoke initial trompeur** : v2.0.0 testait 4 vecteurs garak hostiles + 1 fiche legit. Faux sens de sécurité — manque les **questions M&A baseline diversifiées**. v2.1 ajoute mode `smoke-deep` avec 10 questions diversifiées non-hostiles.
2. **Détection leak multi-niveau** : v2.0 grep code seulement. Or régression Pappers 2026-05-02 a montré que **code peut être propre + system prompt LLM peut leaker**. v2.1 ajoute 3 niveaux : code statique + system prompt + runtime LLM responses.
3. **Pénalisation QCS** : la formule v2.0 traitait line coverage et clickable coverage avec poids égaux. v2.1 introduit **pénalité régression** : si une dim baisse de > 10pp, QCS minoré de 5 points absolus.
4. **Pièges connus enrichis** : 10 → **13 pièges** (ajout "smoke hostile insuffisant", "code propre ≠ runtime propre", "subagent ne lit pas son output complet").
5. **Mode `regression`** ajouté : 8 points de vérification rapide (Pappers code + LLM, garak v7, datalake, gold MVs, SCRUM epic, PRs, containers).

Tu lances un audit QA sur DEMOEMA en orchestrant le subagent `qa-engineer` selon le scope demandé.

## État courant DEMOEMA (rappel contexte)

- **Niveau de rigueur actuel** : **L2** (Playbook E 14 axes + 100 % cliquables) — cf. doctrine §7 échelle L1-L5
- **Cible décidée 2026-05-02** : **L4 minimum** (QCS ≥ 90 sur 15 dimensions) avant prod payante / release investisseur
- **Plan adoption L2 → L4** : 12 semaines (2026-05-04 → 2026-07-25), 6 sprints, 20 tickets `qa-l4-*`
- **Epic Jira** : [SCRUM-136](https://demoema.atlassian.net/browse/SCRUM-136) + 20 stories (SCRUM-137..156)
- **Audits précédents** : 2 audits QA (110 questions) + 2 rounds garak (HijackHateHumans + latentinjection) — tous patchés
- **Tickets follow-up pending** : SCRUM-122 (sync dashboard↔fiche), SCRUM-133 (press_mentions index)

## 11 modes d'invocation `/qa-audit <type>`

| Mode | Scope | Doctrine §ref | Durée typique |
|---|---|---|---|
| `copilot` | Playbook A — 110 questions copilot LLM (latence, hallucinations, sources) | §4 Playbook A | 1-2 h |
| `security` | Playbook B — garak `promptinject + dan + latentinjection` | §4 Playbook B | 1-2 h |
| `nav` | Playbook C — 8 sections UI navigation hash routing | §4 Playbook C | 30 min |
| `datalake` | Playbook D — **10 sous-axes D.1→D.10** (schéma, ingestion, MV, Soda Core, lineage, perf, RGPD, backup, observability, cohérence cross-source) | §4 Playbook D | 2-3 h |
| `clickables` | Sous-axe 1.bis — **350-400+ éléments cliquables** (boutons, liens, role=*, inputs, select, summary, onclick, tabindex, label) | §5 axe 1.bis | 1 h |
| `browser` ou `navigateur` | Sous-axe 1.ter — **~250 tests sur 18 catégories** (routing, clavier, souris, tactile, clipboard, files, print, persistance, cookies, network, PWA, permissions, a11y, visuel, résilience, perf, window/tab, cross-browser × cross-device) | §5 axe 1.ter | 2 h |
| `backend` | Axe 2 — **10 sous-axes B.1→B.10** (endpoints, Pydantic, SSE, async, errors, auth, rate limit, cache, health, observability) | §5 axe 2 | 1-2 h |
| `minutieux` ou `full` ou `complet` | **Playbook E entier** — 14 axes + 15 dimensions coverage + 11 dimensions complémentaires | §5 Playbook E | 4-8 h |
| `l4` | Audit complet + **calcul QCS** + verdict GO/NO-GO L4 (production payante) | §5 + §7 + §8 | 4-8 h |
| `regression` | **8 points vérif rapide** (Pappers 3-niveaux + garak + datalake + gold MVs + SCRUM epic + PRs + containers + logs erreurs) | §2 leçons + §8 | 10-15 min |
| `smoke-deep` | **10 questions M&A baseline diversifiées** (non-hostiles) → détecte leaks runtime LLM (Pappers, hallucinations, sources fantômes) | §2 + Playbook A | 5-10 min |

Sans argument → demander à l'utilisateur lequel des 11 modes.

## Procédure d'exécution (5 étapes)

### Étape 1 — Charger la doctrine

Lis dans cet ordre :
1. **`docs/QA_PLAYBOOKS.md`** (1782 lignes — source-of-truth complet)
   - §4 Playbooks A/B/C/D
   - §5 Playbook E + 14 axes (axe 1 incluant 1.bis et 1.ter, axe 2 B.1-B.10, axe 4 DATA.1-DATA.10, etc.)
   - §6 15 dimensions coverage (line, branch, mutation, API, clickable, LLM tool, data quality, visual, browser, device, locale, persona, state, negative)
   - §7 5 niveaux rigueur L1→L5
   - §8 Plan adoption L2→L4 12 semaines
   - §9 11 dimensions complémentaires (architecture, audit M&A, time, numeric, concurrency, DX agentic, crisis comm, vendor exit, test pyramid, knowledge mgmt, license)
2. **`audit_demoema/AUDIT_QA_RAPPORT.md`** (corpus baseline 110 questions, métriques avant/après)
3. **`garak_demoema/demoema_copilot.json`** (config red-team si security)
4. **`docs/ETAT_REEL_2026-05-01.md`** (snapshot état post-audit round 1)

### Étape 2 — Vérifier prérequis

Selon le scope :

| Mode | Prérequis à vérifier |
|---|---|
| `copilot` | Endpoint `/api/copilot/redteam` UP : `curl -sS https://82-165-57-191.sslip.io/api/health \| jq .` |
| `security` | Idem + venv garak : `ls /c/Users/zkhch/garak_demoema/.venv/Scripts/python.exe` |
| `datalake` | SSH VPS readonly : `ssh -i ~/.ssh/demoema_ionos_ed25519 root@82.165.57.191 'echo OK'` + Soda Core : `pip show soda-core-postgres` |
| `nav`/`clickables`/`browser` | Chrome DevTools MCP dans session OU Playwright : `cd frontend && npx playwright --version` |
| `backend` | OpenAPI à jour : `curl -sS https://82-165-57-191.sslip.io/openapi.json \| jq '.paths \| keys \| length'` |
| `minutieux`/`full`/`l4` | TOUS les ci-dessus |

Si un prérequis manque :
- Outils OSS non installés (DeepEval, Promptfoo, Hypothesis, Splink, Soda Core, Schemathesis, mutmut) → ouvrir ticket adoption sprint QA-N (cf. doctrine §3 roadmap)
- Infra (VPS, Postgres, Caddy) → escalade `devops-sre` subagent
- Endpoint prod KO → STOP audit, alerte Slack

### Étape 3 — Lancer le subagent qa-engineer

Délègue via `Agent` tool avec `subagent_type=qa-engineer` et prompt structuré (template selon scope) :

```
Lance le Playbook <X> selon docs/QA_PLAYBOOKS.md §<Y>.

Contexte DEMOEMA :
- Cible prod : https://82-165-57-191.sslip.io
- Stack : FastAPI + Next.js 15 + Postgres datalake (15M rows) + DeepSeek LLM
- Niveau rigueur : L2 actuel, cible L4 (QCS >= 90)
- Baseline (cf §2 doctrine) : p50 copilot 10s, p95 18s, 0 hallucination DL{N},
  0 source pappers, 350-400+ cliquables, 14 axes, 15 dim coverage

Périmètre <X> :
- <Pour clickables : axe 1.bis 350-400+ éléments via clickables-exhaustive.spec.ts>
- <Pour browser : axe 1.ter 18 catégories A-R, 250 tests Playwright>
- <Pour datalake : 10 sous-axes D.1->D.10, Soda Core scans, RGPD audit>
- <Pour backend : 10 sous-axes B.1->B.10, Schemathesis stateful, OWASP API Top 10>

Outils à utiliser (versions stables 2026-05) :
- garak v0.15.0 (Agent breaker probe + ModernBERT + mTLS REST)
- Schemathesis 4.17 `st fuzz` stateful
- DeepEval 3.9.9 (ToolCorrectness, TaskCompletion, PlanAdherence)
- Promptfoo 0.121.9 (Trajectory eval + HarmBench filter)
- Playwright 1.59.1 (browser.bind() + --debug=cli)
- @axe-core/playwright + axe-core 4.11.4
- MemLab heap snapshots
- Hypothesis 6.151+ (property-based)
- Splink (entity resolution)
- Soda Core (data quality YAML)
- TLA+ (verification formelle)

Output requis :
1. Rapport `audit_demoema/AUDIT_<TYPE>_<DATE>.md` (format §5 ci-dessous)
2. Verdict GO/NO-GO par axe et sous-axe
3. Métriques chiffrées avant/après baseline (delta pp par dimension)
4. Pour chaque NO-GO : recommander subagent cible (backend-engineer / frontend-engineer / devops-sre / lead-data-engineer / atlassian-sync)
5. Tickets SCRUM proposés (sous epic SCRUM-136 si L4-related)

PIÈGES À ÉVITER (cf. §2 leçons) :
- Sampler outputs garak avant de patcher (faux positifs FR mitigation.MitigationBypass)
- Ne pas confondre `dan.Ablation` 100% fail (cap 2000 chars OK) avec vraie vuln
- CJK encoding : payloads via fichier UTF-8, pas via shell -d
- Probes garak valides : promptinject + dan + latentinjection (PAS sysprompt_extraction)
- Bouton fantôme = 0 effet (nav/DOM/network/aria) → fail axe 1.bis
- PII dirigeants en logs = fail axe D.7 RGPD

NE JAMAIS :
- Modifier code prod (DETECTE et REPORTE uniquement)
- Push / merge / déployer
- Inventer outils non installés (verifier `pip show` / `npm ls` avant)
- Conclure PASS sans chiffres (toujours latences + fail rates + QCS)
```

### Étape 4 — Calculer le Quality Coverage Score (QCS)

Si scope = `minutieux`/`full`/`l4`, après l'audit :

**Formule QCS** (moyenne pondérée des 15 dimensions normalisées 0-100) :
```
QCS = ROUND(
  0.10 * line_coverage_pct +
  0.10 * branch_coverage_pct +
  0.05 * path_coverage_pct +
  0.10 * mutation_coverage_pct +
  0.08 * api_endpoint_coverage_pct +
  0.10 * clickable_coverage_pct +
  0.08 * llm_tool_coverage_pct +
  0.08 * data_quality_coverage_pct +
  0.05 * visual_regression_coverage_pct +
  0.05 * browser_coverage_pct +
  0.04 * device_coverage_pct +
  0.03 * locale_coverage_pct +
  0.03 * persona_coverage_pct +
  0.05 * state_coverage_pct +
  0.06 * negative_test_coverage_pct
, 1)
```

Total poids = 1.00. Comparer aux seuils :
- **L2** (actuel) : QCS ≥ 55
- **L3** (Q3 2026) : QCS ≥ 80
- **L4** (cible 2026-07-25) : QCS ≥ 90 ⬅
- **L5** (2028+) : QCS ≥ 95

### Étape 5 — Reporter au user (format obligatoire)

```markdown
# Audit QA <type> — DEMOEMA <date> (<git_sha>)

## Verdict global

**GO / NO-GO** (production payante L4)
**QCS courant** : <X>/100 (cible L4 = 90, baseline L2 ≈ 55)
**Niveau de rigueur atteint** : L<N>

## Métriques chiffrées vs baseline

| Métrique | Baseline | Run | Delta | Cible | Verdict |
|---|---|---|---|---|---|
| p50 copilot SSE | 10 s | <X> s | <Δ> | <5 s | <emoji> |
| p95 copilot SSE | 18 s | <Y> s | <Δ> | <30 s | <emoji> |
| Hallucinations DL{N} | 0/110 | <N>/110 | <Δ> | 0 | <emoji> |
| Source pappers | 0/110 | <N>/110 | <Δ> | 0 | <emoji> |
| Cliquables PASS (1.bis) | 100 % | <X>% | <Δ> | 100 % | <emoji> |
| Tests browser PASS (1.ter) | <baseline>% | <X>% | <Δ> | 100 % | <emoji> |
| Mutation score | <X>% | <Y>% | <Δ> | 90 % L4 | <emoji> |
| Soda Core checks | <X>/<total> | <Y>/<total> | <Δ> | 100 % | <emoji> |
| ... (15 dimensions) | ... | ... | ... | ... | ... |

## Bugs détectés (priorisés)

### [P0] <titre du bug critique>
- **Reproduction** : <étapes>
- **Impact** : <user/business impact>
- **Cause probable** : <hypothèse>
- **Fix recommandé** : <description> → délégué à `<subagent-cible>` (`backend-engineer` / `frontend-engineer` / `devops-sre` / `lead-data-engineer`)
- **Ticket SCRUM proposé** : `[<priorité>] <titre>` sous epic SCRUM-136

### [P1] ... etc

## Faux positifs documentés (à NE PAS patcher)

<liste des fail rates suspects qui sont en réalité des faux positifs, avec sample d'outputs réels>

## Régressions vs sprint précédent

| Dimension | Sprint N-1 | Sprint N | Delta | Action |
|---|---|---|---|---|
| <Y> | <X> % | <Y> % | <Δ pp> | <à investiguer si > 5 pp> |

## Suite recommandée

- **Re-run après patches** : `<commande exacte>` (ex: `/qa-audit security` après merge PR fix)
- **Tickets SCRUM à créer** : <liste avec key proposée>
- **Schedule remote agent** : <oui/non + date> pour vérification follow-up

## Conformité critères GO L4 (10 obligatoires, cf §8)

- [<x|>] QCS ≥ 90 (actuel : <N>)
- [<x|>] 14 axes Playbook E tous GO
- [<x|>] 350-400+ cliquables 100 % PASS (1.bis)
- [<x|>] 250 tests browser 100 % PASS (1.ter)
- [<x|>] Mutation score ≥ 90 % sur 5 modules critiques
- [<x|>] 0 finding SAST/DAST high+
- [<x|>] TLA+ verification formelle invariants OK
- [<x|>] Disparate impact < 0.8 (fairness scoring M&A)
- [<x|>] Chaos Game Day RTO < 15 min
- [<x|>] Endurance 24h + 7j sans memory leak

**Verdict final L4** : <GO si 10/10> | <NO-GO + blockers listés>
```

## Exemples d'invocation complets

```bash
/qa-audit copilot       → Playbook A : 110 questions copilot, 1-2h
/qa-audit security      → Playbook B : garak promptinject+dan+latentinjection, 1-2h
/qa-audit nav           → Playbook C : 8 sections UI hash routing, 30min
/qa-audit datalake      → Playbook D : 10 sous-axes D.1→D.10, 2-3h
/qa-audit clickables    → axe 1.bis : 350-400+ éléments interactifs, 1h
/qa-audit browser       → axe 1.ter : 250 tests browser (18 catégories) × 8 projets cross-browser, 2h
/qa-audit backend       → axe 2 : 10 sous-axes B.1→B.10 endpoints/SSE/auth/cache, 1-2h
/qa-audit minutieux     → Playbook E entier : 14 axes + 15 dim + 11 dim, 4-8h
/qa-audit l4            → audit complet + QCS + verdict GO/NO-GO production payante, 4-8h
```

## Si erreur subagent (gestion exceptions)

- **Subagent timeout (> 30 min sans output)** : kill + relancer avec scope réduit (sous-axe par sous-axe)
- **Subagent retourne erreur ou fail systématique** : afficher l'erreur intégrale au user + escalade `devops-sre`
- **Prérequis manquant détecté en cours de route** : pause audit, log précis du manque, proposer `/qa-audit <scope_réduit>` excluant la dimension bloquée
- **Conflit avec autre audit en cours** : refuser nouveau lancement, informer du run en cours
- **Endpoint prod 5xx en milieu d'audit** : freeze rapport partiel, alerte `devops-sre`, ne pas continuer

## Pièges connus à NE PAS reproduire (cf. doctrine §2 leçons techniques)

1. **Faux positifs garak** `dan.*/mitigation.MitigationBypass` 80-100 % fail = détecteur EN sur copilot FR. **Toujours sampler les outputs avant de conclure.**
2. **Regex `\b` global** dans `_PROMPT_INJECTION_PATTERNS` casse les patterns commençant par `[`/`<`/CJK. Vérifier que le `\b` est local par alternative.
3. **CJK encoding bash** : `curl -d '{"q":"哈哈"}'` corrompu sur Windows. Toujours `-d @file.json` UTF-8.
4. **Nom de probe `sysprompt_extraction`** N'EXISTE PAS dans garak v0.14/v0.15. Utiliser uniquement `promptinject + dan + latentinjection`.
5. **Bouton "fantôme"** : un cliquable sans effet (handler vide, `console.log` only) = fail axe 1.bis. Pattern de détection : 4 effets attendus (nav / DOM mutation / network / aria-state).
6. **Source `pappers`** abandonnée 2026-04-23 → grep doit retourner 0 dans réponses copilot **ET dans system prompt LLM ET dans tools MCP** (3 niveaux à tester, cf. piège 12).
7. **PII dirigeants en logs** : nom/prénom en clair = fail axe D.7 RGPD. Hash uniquement.
8. **`dan.Ablation_Dan_11_0` 100 % fail** = sécurité d'input cap 2000 chars qui marche, PAS une vuln.
9. **Test rejette payload chinois** : si test échoue sur `哈哈被耍`, vérifier d'abord encoding bash (Windows) avant de patcher la regex.
10. **Cliquables sans test si caché derrière un autre élément** : `:visible` Playwright ne capte pas les `display:none`, mais peut capter les `visibility:hidden` → bien filtrer.
11. **Smoke hostile insuffisant** ⚡ NOUVEAU 2026-05-02 : tester 4-5 vecteurs garak hostiles ne couvre PAS les fuites en mode user normal. **TOUJOURS** ajouter 10 questions M&A baseline non-hostiles (`fiche EQUANS`, `top cibles tech IDF`, `BODACC Bretagne`, etc.). Sinon faux sens de sécurité.
12. **Code propre ≠ runtime propre** ⚡ NOUVEAU : régression Pappers 2026-05-02 a montré que `grep pappers backend/` peut retourner 0 occurrences ET le copilot LLM continue à dire "Pappers MCP" dans ses réponses. **3 niveaux à tester** : (a) code source, (b) system prompt `_SYSTEM_PROMPT_TOOLS`, (c) runtime LLM responses. Le test pytest `test_no_pappers_leak.py` couvre les 3 niveaux.
13. **Subagent ne lit pas son output complet** ⚡ NOUVEAU : si je lance un subagent qa-engineer en background et qu'il revient avec "audit OK", **toujours sampler son output JSONL** avant de relayer "GO" au user. Le subagent peut résumer trop optimistement.

## Ne JAMAIS faire

- **Modifier code prod** : qa-engineer DETECTE et REPORTE, ne patche pas. Délégation aux subagents `backend-engineer` / `frontend-engineer` / `devops-sre` / `lead-data-engineer`.
- **Push sur main / merge PR / déployer** : chain humaine sur écritures critiques. Le skill propose les patches mais Zak les valide.
- **Inventer des outils non installés** : DeepEval, Promptfoo, Stagehand, Splink, Soda Core, Hypothesis, mutmut, Schemathesis, etc. → vérifier `pip show <pkg>` ou `npm ls <pkg>` AVANT de prétendre les utiliser. Si non installé → ouvrir ticket adoption sprint QA-N.
- **Conclure "PASS" sans chiffres** : toujours `p50=Xs, p95=Ys, fail_rate=Z%, QCS=N/100, mutation=M%`. Pas de "ça a l'air OK" / "tout est vert".
- **Skip un sous-axe sans justification écrite** : chaque sous-axe non testé doit avoir une raison documentée dans le rapport (ex: "outil X non installé, ticket SCRUM-Y créé").
- **Faire des actions payantes** : pas de SaaS payant (Galileo, Patronus, Confident AI cloud, Chromatic, BrowserStack) sans approbation explicite Zak.
- **Toucher au datalake en write** : SSH VPS readonly uniquement, pas de SQL UPDATE/DELETE/CREATE INDEX sans validation.

## Références

- **Doctrine** : `docs/QA_PLAYBOOKS.md` (1782 lignes)
- **Subagent** : `.claude/agents/qa-engineer.md` (178 lignes)
- **Epic Jira** : [SCRUM-136](https://demoema.atlassian.net/browse/SCRUM-136) "[QA L4] Adoption rigueur niveau L4"
- **Stories** : SCRUM-137..156 (20 disciplines L3+L4 réparties sur 6 sprints)
- **Repo** : https://github.com/Zakariakhchiche/DEMOEMA
- **Audits historiques** : `audit_demoema/` (rapports + screenshots) + `garak_demoema/` (red-team)
- **PR doctrine** : #102 (mergée), commits `8291d0a → 3f85f3a` sur main
