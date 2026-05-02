---
name: qa-audit
version: 2.2.0
description: Lance un audit QA DEMOEMA selon un des 5 playbooks (A/B/C/D/E) ou un sous-axe ciblé. Use when l'utilisateur demande "lance un audit", "teste tout", "audit copilot", "audit security", "audit datalake", "audit nav", "audit clickables", "audit browser", "audit backend", "audit minutieux", "audit l4", "audit régression", "audit smoke-deep", ou veut vérifier l'état QA avant une release. Le skill délègue au subagent qa-engineer après avoir résolu le scope.
allowed-tools:
  - Read
  - Bash
  - Grep
  - Glob
  - Agent
  - TaskCreate
  - TaskUpdate
  - WebFetch
  - WebSearch
  - mcp__chrome-devtools__navigate_page
  - mcp__chrome-devtools__take_snapshot
  - mcp__chrome-devtools__take_screenshot
  - mcp__chrome-devtools__evaluate_script
  - mcp__chrome-devtools__list_console_messages
  - mcp__chrome-devtools__list_network_requests
  - mcp__chrome-devtools__click
  - mcp__chrome-devtools__fill
  - mcp__chrome-devtools__lighthouse_audit
  - mcp__chrome-devtools__performance_start_trace
  - mcp__chrome-devtools__performance_stop_trace
  - mcp__chrome-devtools__performance_analyze_insight
  - mcp__chrome-devtools__take_memory_snapshot
  - mcp__chrome-devtools__wait_for
  - mcp__chrome-devtools__emulate
---

# QA Audit DEMOEMA — Skill orchestrateur (v2.2.0, 2026-05-02)

## Changelog v2.0/2.1 → v2.2.0 (peer review a révélé 10 bugs)

**Bugs P0 corrigés (4)** :
1. **Désync taille doctrine** : ne plus hardcoder le count de lignes. Le subagent et le skill lisent le **header YAML doctrine** dans `docs/QA_PLAYBOOKS.md` (single source of truth).
2. **Désync nombre de modes** : la liste des modes vit uniquement dans le header YAML doctrine. Skill et subagent référencent ce header.
3. **Pénalité régression** : maintenant **codée explicitement** dans la formule QCS (et pas juste annoncée).
4. **`/openapi.json` 404 prereq** : accepter 404 prod (intentionnel sécurité) + fallback `backend/openapi.yaml` local pour Schemathesis.

**Bugs P1 corrigés (3)** :
5. Test runtime `test_no_pappers_leak` parallélisé via `pytest.mark.asyncio` + cache-bust UUID + split unit/integration.
6. **Wildcard `mcp__chrome-devtools__*` remplacé** par liste explicite des 15 tools Chrome MCP nécessaires (cf. frontmatter).
7. **Versions outils** garak/Schemathesis/etc. **ne sont plus hardcodées** : runtime check via `pip show` au démarrage.

**Bugs P2 corrigés (3)** :
8. **Whitelist stricte des modes** au démarrage (anti-injection commande).
9. **Mode `l4` monolithique → 7 sous-modes** `l4-step1` à `l4-step6` + `l4-final` alignés sur les 6 sprints §8.
10. **Concurrence** : timestamp `HHMMSS` dans nom rapport + lockfile `audit_demoema/.lock`.

**3 améliorations intégrées** :
- Single-source-of-truth via header YAML doctrine + script `scripts/check_doctrine_sync.py` en CI.
- Mode L4 incremental + pénalité régression dans formule.
- **`smoke-deep` en gate pré-requis OBLIGATOIRE** de tous les modes (sauf `regression`/`smoke-deep` lui-même).

## État courant DEMOEMA

- **Niveau rigueur actuel** : **L2** (Playbook E 14 axes + 100 % cliquables) — cf. doctrine §7
- **Cible décidée 2026-05-02** : **L4 minimum** (QCS ≥ 90) avant prod payante
- **Plan adoption L2 → L4** : 12 semaines / 6 sprints / 20 tickets `qa-l4-*`
- **Epic Jira** : [SCRUM-136](https://demoema.atlassian.net/browse/SCRUM-136) + 20 stories (SCRUM-137..156) + SCRUM-157 (Pappers purge P0)
- **QCS courant estimé** : ~2-3 / 100 (audit régression 2026-05-02)
- **Régressions actives** : Pappers leak runtime LLM (4/5 questions M&A baseline)

## Modes d'invocation `/qa-audit <type>`

**Source-of-truth** : la liste des modes est dans `docs/QA_PLAYBOOKS.md` header YAML (clé `modes`). Si le user invoque un mode non listé → STOP + lister les modes valides.

| Mode | Scope | Doctrine §ref | Durée |
|---|---|---|---|
| `smoke-deep` ⚡ | **Gate prérequis OBLIGATOIRE** : 10 questions M&A baseline diversifiées non-hostiles → détecte fuites runtime LLM | §2 leçons | **5-10 min** |
| `regression` | 8 points vérif rapide (Pappers 3-niveaux + garak v7 + datalake + gold MVs + SCRUM epic + PRs + containers + logs) | §2 + §8 | 10-15 min |
| `copilot` | Playbook A — 110 questions copilot LLM | §4 Playbook A | 1-2 h |
| `security` | Playbook B — garak `promptinject + dan + latentinjection` | §4 Playbook B | 1-2 h |
| `nav` | Playbook C — 8 sections UI navigation hash routing | §4 Playbook C | 30 min |
| `datalake` | Playbook D — 10 sous-axes D.1→D.10 | §4 Playbook D | 2-3 h |
| `clickables` | Sous-axe 1.bis — 350-400+ éléments cliquables | §5 axe 1.bis | 1 h |
| `browser` (`navigateur`) | Sous-axe 1.ter — ~250 tests sur 18 catégories | §5 axe 1.ter | 2 h |
| `backend` | Axe 2 — 10 sous-axes B.1→B.10 | §5 axe 2 | 1-2 h |
| `l4-step1` | Coverage backend + Hypothesis property-based (Sprint S1) | §8 sprint 1 | 4 h |
| `l4-step2` | Mutation testing + Schemathesis fuzz (Sprint S2) | §8 sprint 2 | 6 h |
| `l4-step3` | Playwright clickables + browser + a11y (Sprint S3) | §8 sprint 3 | 8 h |
| `l4-step4` | Contracts Pact + LLM judge panel + fairness (Sprint S4) | §8 sprint 4 | 6 h |
| `l4-step5` | TLA+ + SBOM + SAST/DAST + A/B shadow (Sprint S5) | §8 sprint 5 | 8 h |
| `l4-step6` | Dashboard 15D + audit final (Sprint S6) | §8 sprint 6 | 5 h |
| `l4-final` | Agrégation des 6 steps + verdict GO/NO-GO global L4 | §8 final | 1 h |
| `minutieux` / `full` / `complet` | Playbook E entier (alias séquentiel l4-step1+...+l4-step6) | §5 Playbook E | **24-48 h wall-clock** |

⚠️ Note honnêteté : `minutieux`/`full`/`complet` = wall-clock 24-48h en réalité (pas 4-8h comme v2.1 disait). Effort total ≈ 46 j-h selon §8.

Sans argument → demander à l'utilisateur lequel des modes (lister depuis header YAML).

## Procédure d'exécution (6 étapes — ajout étape 0 + 1.5)

### Étape 0 — Validation du mode (NOUVEAU v2.2)

```bash
# Lire la whitelist depuis le header YAML doctrine (anti-injection)
VALID_MODES=$(python -c "
import re, sys
src = open('docs/QA_PLAYBOOKS.md').read()
m = re.search(r'<!--\s*DOCTRINE_HEADER_START.*?\n\`\`\`yaml\n(.*?)\n\`\`\`\s*<!--\s*DOCTRINE_HEADER_END', src, re.DOTALL)
in_modes = False
for line in m.group(1).splitlines():
    if line.startswith('modes:'): in_modes = True; continue
    if in_modes and line.startswith('  - '): print(line[4:].strip())
    elif in_modes and line and not line.startswith(' '): break
")

if ! echo "$VALID_MODES" | grep -qx "$USER_MODE"; then
  echo "Mode invalide. Modes valides :"; echo "$VALID_MODES"
  exit 1
fi

# Lock concurrence
LOCKFILE="audit_demoema/.lock"
[ -f "$LOCKFILE" ] && { echo "Audit en cours (cf $LOCKFILE)"; exit 1; }
echo "$$ $(date -u +%Y-%m-%dT%H:%M:%SZ) $USER_MODE" > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT
```

### Étape 1 — Charger la doctrine (via header YAML)

Lis dans cet ordre :
1. **`docs/QA_PLAYBOOKS.md`** — extraire le header YAML pour `doctrine_version`, `modes`, `axes_count`, `dimensions_qcs`, `qcs_thresholds`. Puis lire les sections §X selon scope.
2. **`audit_demoema/AUDIT_QA_RAPPORT.md`** (corpus baseline 110 questions)
3. **`garak_demoema/demoema_copilot.json`** (config red-team si security)
4. **`docs/ETAT_REEL_<latest>.md`** (snapshot état post-audit le plus récent)

### Étape 1.5 — `smoke-deep` GATE OBLIGATOIRE (NOUVEAU v2.2)

**Sauf si mode = `regression` ou `smoke-deep` lui-même**, exécuter d'abord `smoke-deep` :

```python
# 10 questions M&A baseline diversifiées NON-HOSTILES
queries = [
    "fiche EQUANS",
    "scoring SIREN 552081317",
    "top 10 cibles tech IDF",
    "BODACC cessions Bretagne 30 derniers jours",
    "compare LVMH Kering Hermes",
    "dirigeant Bernard Arnault",
    "concurrents EDF dans le 75",
    "entreprises NAF 6201Z avec CA > 50M EUR",
    "signaux M&A semaine derniere",
    "fiche dirigeant senior agroalimentaire 60+",
]
# Pour chaque : POST /api/copilot/redteam, vérifier 0 mention "pappers"
# + 0 hallucination "département N" si pas dans query
# + source != "pappers"
# Si une seule fail → STOP audit, escalade backend-engineer P0
```

Si `smoke-deep` échoue → arrêter l'audit, créer ticket SCRUM P0 immédiat, ne pas continuer le scope demandé. Empêche un audit `l4` qui passerait avec QCS=85 alors que runtime LLM est régressé.

### Étape 2 — Vérifier prérequis avec versions runtime (corrigé v2.2)

Versions outils : check via `pip show <pkg>` au runtime (pas hardcoder dans skill).

| Mode | Prérequis | Action si KO |
|---|---|---|
| `smoke-deep`/`regression`/`copilot` | `curl /api/health` 200 | STOP + escalade devops-sre |
| `security` | venv garak existe + version >= 0.14.1 (vérif au runtime) | Ouvrir ticket adoption upgrade garak |
| `datalake` | SSH VPS readonly + Soda Core installé | Ouvrir ticket adoption Soda Core |
| `nav`/`clickables`/`browser` | Chrome DevTools MCP OU Playwright installé | Ouvrir ticket adoption Playwright |
| `backend` | OpenAPI accessible (3 fallbacks) : (1) `https://prod/openapi.json` (2) `https://prod/api/openapi.json` (3) fichier local `backend/openapi.yaml`. **Si tous 404** → fallback grep `@app.get/post` dans code source pour énumérer endpoints. |
| `l4-step*`/`minutieux` | TOUS les ci-dessus + version sprint correspondante atteinte selon §8 |

### Étape 3 — Lancer le subagent qa-engineer

Délègue via `Agent` avec template structuré. Le prompt référence le **header YAML doctrine** (pas hardcoder versions/modes). **Sample obligatoire de l'output JSONL avant de relayer "GO" au user** (cf. piège 13).

### Étape 4 — Calculer le QCS avec PÉNALITÉ RÉGRESSION (corrigé v2.2)

```python
def compute_qcs(metrics_current, metrics_previous=None):
    """
    metrics: dict[str, float]  # 15 dimensions, valeurs 0-100
    Returns: dict {qcs, base, penalty, regressions}
    """
    weights = {
        "line_coverage_pct": 0.10,
        "branch_coverage_pct": 0.10,
        "path_coverage_pct": 0.05,
        "mutation_coverage_pct": 0.10,
        "api_endpoint_coverage_pct": 0.08,
        "clickable_coverage_pct": 0.10,
        "llm_tool_coverage_pct": 0.08,
        "data_quality_coverage_pct": 0.08,
        "visual_regression_coverage_pct": 0.05,
        "browser_coverage_pct": 0.05,
        "device_coverage_pct": 0.04,
        "locale_coverage_pct": 0.03,
        "persona_coverage_pct": 0.03,
        "state_coverage_pct": 0.05,
        "negative_test_coverage_pct": 0.06,
    }
    assert abs(sum(weights.values()) - 1.0) < 0.001  # poids = 1.00

    base_qcs = round(sum(weights[k] * metrics_current.get(k, 0) for k in weights), 1)

    # PÉNALITÉ RÉGRESSION (NOUVEAU v2.2)
    penalty = 0
    regressions = []
    if metrics_previous:
        for dim in weights:
            prev = metrics_previous.get(dim, 0)
            curr = metrics_current.get(dim, 0)
            if prev - curr > 10:  # baisse > 10pp
                regressions.append((dim, round(prev - curr, 1)))
        if regressions:
            penalty = 5  # -5 pts absolus si AU MOINS UNE dim régresse > 10pp

    final_qcs = max(0, base_qcs - penalty)
    return {"qcs": final_qcs, "base": base_qcs, "penalty": penalty, "regressions": regressions}
```

Seuils (depuis header YAML doctrine `qcs_thresholds`) :
- L2 ≥ 55, L3 ≥ 80, L4 ≥ 90, L5 ≥ 95

### Étape 5 — Reporter au user (timestamp HHMMSS pour éviter écrasement)

```bash
TIMESTAMP=$(date -u +%Y-%m-%dT%H%M%S)
REPORT="audit_demoema/AUDIT_${USER_MODE^^}_${TIMESTAMP}.md"
```

Format obligatoire :
- Verdict GO/NO-GO + QCS + delta vs precedent
- Tableau métriques chiffrées vs baseline (15 dimensions)
- Bugs P0/P1/P2 avec délégation subagent cible
- **Régressions explicites** : si pénalité QCS appliquée, lister les dims qui ont baissé
- Faux positifs documentés
- Suite recommandée avec tickets SCRUM

## Modes ROUTING TABLE (v2.2)

| Mode | Étape 1.5 smoke-deep gate ? | Étape 4 calcul QCS ? |
|---|---|---|
| `smoke-deep` | ✗ (c'est lui-même) | ✗ |
| `regression` | ✗ (utilité = check rapide indépendant) | ✗ |
| `copilot`/`security`/`nav`/`datalake`/`clickables`/`browser`/`backend` | ✓ obligatoire | ✗ partiel |
| `l4-step1`..`l4-step6` | ✓ obligatoire | ✓ partiel (dimensions du sprint) |
| `l4-final`/`minutieux`/`full`/`complet` | ✓ obligatoire | ✓ complet (15 dim + pénalité) |

## Si erreur subagent / timeout

- **Timeout > 30 min sans output** : kill + scope réduit + ouvrir ticket SCRUM P0
- **Erreur systématique** : afficher erreur intégrale + escalade devops-sre
- **Prérequis manquant en route** : pause + ticket adoption + reprendre scope réduit
- **Conflit lockfile** : refuser + indiquer le run en cours (`cat audit_demoema/.lock`)
- **Endpoint prod 5xx mid-audit** : freeze rapport partiel + alerte devops-sre
- **JSONL output malformé** : sampler les 50 dernières lignes + ouvrir ticket parser
- **Subagent retourne "GO" trop optimiste** : SAMPLER son output complet avant relayer ; si écart entre claim et evidence → ne pas relayer GO

## Pièges connus à NE PAS reproduire (16 pièges total)

1. **Faux positifs garak** `dan.*/mitigation.MitigationBypass` 80-100 % fail = détecteur EN sur copilot FR. Sampler avant conclure.
2. **Regex `\b` global** dans `_PROMPT_INJECTION_PATTERNS` casse les patterns `[`/`<`/CJK.
3. **CJK encoding bash** : `curl -d '{"q":"哈哈"}'` corrompu Windows. Toujours `-d @file.json` UTF-8.
4. **Probe `sysprompt_extraction`** N'EXISTE PAS dans garak v0.14/v0.15.
5. **Bouton fantôme** : 0 effet (handler vide) = fail axe 1.bis. 4 effets attendus (nav / DOM / network / aria).
6. **Source `pappers`** abandonnée → grep doit retourner 0 dans (a) code, (b) system prompt LLM, (c) runtime LLM responses (3 niveaux).
7. **PII dirigeants en logs** : nom/prénom en clair = fail axe D.7 RGPD. Hash uniquement.
8. **`dan.Ablation_Dan_11_0` 100 % fail** = sécurité d'input cap 2000 chars OK, PAS une vuln.
9. **Test rejette payload chinois** : vérifier d'abord encoding bash avant de patcher la regex.
10. **Cliquables :visible Playwright** ne capte pas `display:none`, capte `visibility:hidden` → bien filtrer.
11. **Smoke hostile insuffisant** : tester 4-5 vecteurs garak hostiles ne couvre PAS les fuites en mode user normal. **TOUJOURS** ajouter le `smoke-deep` gate.
12. **Code propre ≠ runtime propre** : `grep pappers backend/` peut retourner 0 ET le copilot LLM continue à dire "Pappers MCP". Tester les 3 niveaux (cf. piège 6).
13. **Subagent ne lit pas son output complet** : sampler le JSONL avant de relayer "GO" au user.
14. **NOUVEAU v2.2 — Wildcard MCP `mcp__*__*` non documenté Anthropic** : lister les tools MCP explicitement dans `allowed-tools` (cf. frontmatter ce fichier). Sinon tools rejetés silencieusement.
15. **NOUVEAU v2.2 — Versions outils hardcodées** dans skill = inventées (cf. règle "Ne jamais inventer outils non installés"). Toujours `pip show <pkg>` au runtime.
16. **NOUVEAU v2.2 — `/openapi.json` 404 prod** = peut-être intentionnel sécurité. Fallback : (a) `/api/openapi.json`, (b) fichier local `backend/openapi.yaml`, (c) grep `@app.get/post` dans code.

## Ne JAMAIS faire

- Modifier code prod (DETECTE + REPORTE uniquement)
- Push / merge / déployer (chain humaine sur écritures critiques)
- Inventer outils non installés (vérifier `pip show` / `npm ls` au runtime)
- Conclure PASS sans chiffres (toujours `p50=Xs, p95=Ys, fail_rate=Z%, QCS=N/100`)
- Skip un sous-axe sans justification écrite
- Faire des actions payantes (Galileo, Patronus, Confident AI cloud, Chromatic, BrowserStack) sans approbation Zak
- Toucher au datalake en write (SSH readonly only)
- Relayer "GO" du subagent sans avoir sampler son output complet (piège 13)
- Lancer 2 audits en parallèle (lockfile)

## Références

- **Doctrine** : `docs/QA_PLAYBOOKS.md` (header YAML = source-of-truth versions/modes/axes)
- **Subagent** : `.claude/agents/qa-engineer.md`
- **Sync check CI** : `scripts/check_doctrine_sync.py`
- **Epic Jira** : [SCRUM-136](https://demoema.atlassian.net/browse/SCRUM-136) + 20 stories + SCRUM-157 (Pappers P0)
- **Test no_pappers_leak** : `backend/tests/test_no_pappers_leak.py` (3 niveaux : code + system prompt + runtime)
- **Repo** : https://github.com/Zakariakhchiche/DEMOEMA
- **PRs récentes** : #102 (doctrine, mergée), #106 (bootstrap outils, FERMÉE par décision Zak en attente résolution Pappers)
