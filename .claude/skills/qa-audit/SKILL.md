---
name: qa-audit
description: Lance un audit QA DEMOEMA selon un des 5 playbooks (A/B/C/D/E). Use when l'utilisateur demande "lance un audit", "teste tout", "audit copilot", "audit security", "audit datalake", "audit nav", "audit minutieux", ou veut vérifier l'état QA avant une release. Le skill délègue au subagent qa-engineer après avoir résolu le scope.
allowed-tools: [Read, Bash, Grep, Glob, Agent, TaskCreate, TaskUpdate]
---

# QA Audit DEMOEMA — Skill orchestrateur

Tu lances un audit QA sur DEMOEMA en orchestrant le subagent `qa-engineer` selon le scope demandé par l'utilisateur.

## Arguments attendus (ARG)

L'utilisateur invoque le skill avec un argument optionnel :
- `qa-audit copilot` → Playbook A (110 questions copilot LLM)
- `qa-audit security` → Playbook B (garak red-team latentinjection/promptinject/dan)
- `qa-audit nav` → Playbook C (8 sections UI navigation)
- `qa-audit datalake` → Playbook D (10 sous-axes : schéma, ingestion, MV, Soda Core, lineage, perf, RGPD, backup, observability, cohérence)
- `qa-audit clickables` → axe 1.bis (350-400+ éléments cliquables exhaustifs)
- `qa-audit browser` ou `qa-audit navigateur` → **axe 1.ter complet** (18 catégories, ~250 tests : routing, clavier, souris, tactile, copier/coller, file upload, print, persistance, cookies, network conditions, PWA, permissions, a11y, visuel, résilience, perf, window/tab, cross-browser × cross-device matrix 4×4=8 projets Playwright)
- `qa-audit backend` → axe 2 (10 sous-axes B.1→B.10 : endpoints, Pydantic, SSE, async, errors, auth, rate limit, cache, health, observability)
- `qa-audit minutieux` ou `qa-audit full` ou `qa-audit complet` → **Playbook E entier** (14 axes + 15 dimensions coverage + 11 dimensions complémentaires)
- `qa-audit l4` → audit complet + verdict GO/NO-GO L4 (QCS ≥ 90 ?)
- Sans argument → demander à l'utilisateur lequel des 8 modes

## Procédure d'exécution

### Étape 1 — Charger la doctrine
Lis dans cet ordre :
1. `docs/QA_PLAYBOOKS.md` (1576 lignes — source-of-truth complet)
2. `audit_demoema/AUDIT_QA_RAPPORT.md` (corpus baseline 110 questions)
3. `garak_demoema/demoema_copilot.json` (config red-team si security)

### Étape 2 — Vérifier prérequis
Selon le scope :
- **copilot/security** : endpoint `/api/copilot/redteam` UP via `curl -sS https://82-165-57-191.sslip.io/api/health`
- **datalake** : SSH VPS readonly + Soda Core installé (`pip show soda-core-postgres`)
- **nav/clickables** : Chrome DevTools MCP disponible dans la session OU Playwright (à vérifier)
- **backend** : FastAPI prod accessible + OpenAPI à `/openapi.json`
- **minutieux** : tous les prérequis ci-dessus

Si un prérequis manque → message clair + escalade `devops-sre` si infra.

### Étape 3 — Lancer le subagent qa-engineer
Délègue via `Agent` tool avec subagent_type=`qa-engineer` et prompt structuré :

```
Lance le Playbook <X> selon docs/QA_PLAYBOOKS.md §<Y>.

Contexte :
- Cible prod : https://82-165-57-191.sslip.io
- Baseline : <métriques pertinentes du Playbook>
- Outils à utiliser : <liste depuis le Playbook>

Output requis :
- Rapport au format `audit_demoema/AUDIT_<TYPE>_<DATE>.md`
- Verdict GO/NO-GO par sous-axe
- Métriques chiffrées avant/après baseline
- Pour chaque NO-GO : recommander le subagent cible (backend-engineer / frontend-engineer / devops-sre / lead-data-engineer)

Sample les outputs avant de conclure (faux positifs FR garak connus, cf. Playbook §2 leçons).
```

### Étape 4 — Calculer le QCS (Quality Coverage Score)
Si scope = `minutieux`/`full`/`l4`, après l'audit :
- Récupérer les métriques par dimension (15 coverage + 14 axes)
- Calculer QCS = moyenne pondérée 0-100
- Comparer aux seuils : L2≥55, L3≥80, L4≥90, L5≥95
- Émettre verdict GO/NO-GO L4 (cible Zak 2026-05-02)

### Étape 5 — Reporter au user
Format de réponse :

```markdown
## Audit QA <type> — <date>

**Verdict global** : GO / NO-GO
**QCS courant** : <X>/100 (cible L4 = 90)
**Delta vs baseline** : <Δ pp par dimension critique>

### Bugs détectés
- [P0] <titre> → recommander `<agent-cible>`
- [P1] <titre> → recommander `<agent-cible>`
...

### Régressions vs sprint précédent
- Dimension <Y> baisse de <Z> pp ⚠

### Suite recommandée
- Re-run après patches : `<commande>`
- Tickets SCRUM à créer : <liste>
- Schedule remote agent : `<oui/non>` à <date>
```

## Exemples d'invocation

```
/qa-audit copilot       → 110 questions baseline + métriques
/qa-audit security      → garak promptinject + latentinjection + dan
/qa-audit datalake      → 10 sous-axes D.1→D.10 (Soda Core + lineage + perf)
/qa-audit clickables    → 350-400+ éléments interactifs
/qa-audit minutieux     → Playbook E complet (14 axes + 15 dim + 11 dim)
/qa-audit l4            → audit complet + verdict GO/NO-GO production payante
```

## Pièges connus à NE PAS reproduire (cf. doctrine §2 leçons)

1. **Faux positifs garak** `dan.*/mitigation.MitigationBypass` 80-100 % fail = détecteur EN sur copilot FR. **Toujours sampler les outputs avant de conclure.**
2. **Regex `\b` global** dans `_PROMPT_INJECTION_PATTERNS` casse les patterns commençant par `[`/`<`/CJK. Vérifier que le `\b` est local par alternative.
3. **CJK encoding bash** : `curl -d '{"q":"哈哈"}'` corrompu sur Windows. Toujours `-d @file.json` UTF-8.
4. **Nom de probe `sysprompt_extraction`** N'EXISTE PAS dans garak v0.14/v0.15. Utiliser uniquement `promptinject + dan + latentinjection`.
5. **Bouton "fantôme"** : un cliquable sans effet (handler vide, `console.log` only) = fail axe 1.bis. Pattern de détection : 4 effets attendus (nav / DOM mutation / network / aria-state).
6. **Source `pappers`** abandonnée 2026-04-23 → grep doit retourner 0 dans réponses copilot.
7. **PII dirigeants en logs** : nom/prénom en clair = fail axe D.7 RGPD. Hash uniquement.

## Ne JAMAIS faire

- Modifier code prod (qa-engineer DETECTE et REPORTE, ne patche pas)
- Push sur main / merge / déployer (chain humaine sur écritures critiques)
- Inventer des outils non installés (DeepEval, Promptfoo, Stagehand, Splink, Soda — vérifier `pip show` / `npm ls` avant de prétendre les utiliser)
- Conclure "PASS" sans chiffres (toujours `p50=Xs, p95=Ys, fail_rate=Z%, QCS=N/100`)
- Skip un sous-axe sans justification écrite dans le rapport
