# PLAN PATCH — Audit QA 2026-05-01

> **Source** : `C:\Users\zkhch\audit_demoema\AUDIT_QA_RAPPORT.md`
> **État cible** : `https://82-165-57-191.sslip.io` (VPS IONOS prod)
> **Référence stack** : `docs/ETAT_REEL_2026-04-30.md` (post-scoring v3 PRO)
> **Atlassian** : `demoema.atlassian.net` — Confluence DEMOEMA (id 65942) + Jira SCRUM (84 tickets)
> **Effort total** : 8-12 j-homme · 25 bugs (4 P0 / 9 P1 / 8 P2 / 4 P3)

---

## 0. Pré-requis Atlassian (avant patch)

### Tickets Jira à CRÉER (16 nouveaux)
À créer sous **Epic SCRUM-10 « E6 - Développement MVP »** ou **Epic SCRUM-13 « E9 - Module Compliance »** selon catégorie.

| Code         | Summary                                                         | Epic parent | Prio    | Estimation |
|--------------|-----------------------------------------------------------------|-------------|---------|------------|
| SCRUM-NEW-01 | [P0] Fix hallucination DL{N}→département dans copilot           | SCRUM-10    | Highest | 1 j        |
| SCRUM-NEW-02 | [P0] Fix perte de réponses SSE frontend (race condition)        | SCRUM-10    | Highest | 2-3 j      |
| SCRUM-NEW-03 | [P0] Implémenter ou désactiver hashes #graphe / #comparer       | SCRUM-10    | Highest | 0.5 j      |
| SCRUM-NEW-04 | [P0] Migrer get_fiche_entreprise Pappers → silver.inpi_*        | SCRUM-9     | Highest | 2 j        |
| SCRUM-NEW-05 | [P1] Compléter fiche SSE : EBITDA + NAF lib + score + mandats   | SCRUM-10    | High    | 1-2 j      |
| SCRUM-NEW-06 | [P1] Activer service worker Serwist en prod + fix shortcuts     | SCRUM-10    | High    | 1 j        |
| SCRUM-NEW-07 | [P1] OpenSanctions retry/backoff + fallback cache               | SCRUM-13    | High    | 1 j        |
| SCRUM-NEW-08 | [P1] Synchroniser CA dashboard ↔ fiche (single SoT)             | SCRUM-9     | High    | 1 j        |
| SCRUM-NEW-09 | [P1] Augmenter MAX_ITERATIONS copilot ou paralléliser tools     | SCRUM-10    | High    | 1-2 j      |
| SCRUM-NEW-10 | [P1] Fix tool search_signaux_bodacc — appliquer filtre dept     | SCRUM-13    | High    | 0.5 j      |
| SCRUM-NEW-11 | [P1] Confirmation explicite avant ajout cible (targets_updated) | SCRUM-10    | High    | 0.5 j      |
| SCRUM-NEW-12 | [P2] CTAs contextuels — désafficher si non-sourcing             | SCRUM-10    | Medium  | 0.5 j      |
| SCRUM-NEW-13 | [P2] Reset chat state on "Nouvelle conversation"                | SCRUM-10    | Medium  | 0.5 j      |
| SCRUM-NEW-14 | [P2] Format Md€/M€/€ humain dans Explorer (vs notation 1E9)     | SCRUM-10    | Medium  | 0.5 j      |
| SCRUM-NEW-15 | [P2] Optimiser worker BODACC fetch (COPY vs INSERT)             | SCRUM-9     | Medium  | 2 j        |
| SCRUM-NEW-16 | [P3] Fix hatvp_lobbying rows -1 dans /list-tables               | SCRUM-9     | Low     | 0.25 j     |

### Pages Confluence à mettre à jour (post-patch)
- **5.2 Architecture Technique** (id 66068) — refléter migration Pappers→silver
- **5.4 Data Catalog & Lineage** (id 1146882) — fiche endpoint changé
- **7.6 Self Challenge V3** (id 1245265) — ajouter résultats audit QA 2026-05-01

### Page Confluence à CRÉER
- **7.7 Audit QA 2026-05-01** sous parent 7. Audits (id parent 65942 racine ou parent direct 524328) — copier le rapport audit + ce plan patch.

---

## 1. P0 CRITIQUES — patcher aujourd'hui (jour 1-3)

### P0.1 — Hallucination `DL{N}` → département (SCRUM-NEW-01)
**Symptôme** : `DL28 NAF 7010Z` → réponse filtrée Eure-et-Loir. 6 cas confirmés.
**Localisation** :
- `backend/clients/deepseek.py:865-897` (`_SYSTEM_PROMPT_TOOLS`)
- `backend/clients/deepseek.py:919-922` (composition messages)
- `backend/main.py:1340-1493` (endpoint `/api/copilot/stream`)

**Patch (option A — préprocessing query)** :
```python
# backend/main.py — avant ligne 1342 (passage à copilot_ai_query_stream_with_tools)
import re
LABEL_PREFIX_RE = re.compile(r'^(?:[A-Z]{1,4}\d{1,4}|Q\d+/\d+|DL\d+/\d+|UI\d+)\s*[-:.]?\s*', re.IGNORECASE)
clean_q = LABEL_PREFIX_RE.sub('', q).strip()
# pass clean_q to copilot, garder q pour audit log
```

**Patch (option B — system prompt explicit)** :
```python
# backend/clients/deepseek.py:893 — ajouter avant "RÈGLE CRITIQUE"
"**RÈGLE ANTI-HALLUCINATION** : si la query contient un label en début "
"(ex: DL12, Q5/55, UI3), IGNORE ce label totalement. NE PAS l'interpréter "
"comme département FR, code postal, montant ou tout autre signal. "
"Le label est un identifiant interne de test, pas une donnée métier.\n"
```

**Recommandation** : faire les 2 (defense in depth).

**Test validation** :
```bash
curl -s "https://82-165-57-191.sslip.io/api/copilot/stream?q=DL28%20fiche%20NAF%207010Z" \
  | grep -i "Eure-et-Loir\|département 28" && echo FAIL || echo PASS
```

---

### P0.2 — Frontend perd des réponses sous charge (SCRUM-NEW-02)
**Symptôme** : 5 questions consécutives → SSE backend complète (200), DOM reste figé.
**Localisation** :
- `frontend/src/components/dem/ChatPanel.tsx:374-406` (consommation SSE en parallèle avec fetchTargets)
- `frontend/src/components/dem/ChatPanel.tsx:488-500` (construction réponse)
- `frontend/src/components/dem/ChatPanel.tsx:504-508` (`setConversations` map)
- `frontend/src/components/dem/ChatPanel.tsx:576-594` (rendu `<summary>` toolCalls)

**Cause racine** : `Promise.all([textStreamPromise, cibleSearchPromise, ...])` → race entre `setStreamText` (incrémental) et `setConversations` (final). React 19 batching peut avaler le message final si stream se termine avant le fetch parallèle.

**Patch** :
1. Sortir le SSE consumer dans un hook dédié `useSseStream.ts` avec `useReducer` (transactions atomiques).
2. Remplacer `Promise.all` par `await sequentially` + `flushSync` autour de `setConversations`.
3. Ajouter un `streamId` unique par message — invalider les setState d'un stream obsolète.
4. Ajouter un retry SSE explicite si `reader` close avant `done:true`.

**Test validation** : envoyer 10 questions en 20s → DOM doit rendre 10 blocs `<summary>"X outils utilisés"</summary>`. Fonction de test JS dans le rapport audit (window._countTools).

---

### P0.3 — Liens nav morts `#graphe` / `#comparer` (SCRUM-NEW-03)
**Symptôme** : 2 boutons sur 8 inactifs (25 % de la nav).
**Localisation** :
- `frontend/src/components/dem/TopHeader.tsx:7-16` (TABS — modes `"graph"` et `"compare"`)
- `frontend/src/app/page.tsx:19` (`VALID_MODES`)
- `frontend/src/app/page.tsx:21-25` (`readHashMode()`)
- `frontend/src/app/page.tsx:93-108` (rendu conditionnel — composants existants)

**Cause racine** : nav UI utilise label FR `Graphe`/`Comparer` mais routes JS sont en EN `graph`/`compare`. Le hash `#graphe` n'est pas dans VALID_MODES → fallback `"dashboard"` silencieux.

**Patch** :
```typescript
// frontend/src/app/page.tsx:19
const HASH_ALIASES: Record<string, Mode> = {
  graphe: "graph",
  comparer: "compare",
};
function readHashMode(): Mode {
  if (typeof window === "undefined") return "dashboard";
  const raw = window.location.hash.replace("#", "");
  const aliased = HASH_ALIASES[raw] || raw;
  return VALID_MODES.includes(aliased as Mode) ? (aliased as Mode) : "dashboard";
}
```

OU faire l'inverse côté `TopHeader.tsx` (push `#graph` au lieu de `#graphe`).

**Test validation** : `location.hash = "#graphe"` → `<NetworkGraphView>` rendu, H1 ≠ "Bonjour Anne".

---

### P0.4 — Migrer fiche Pappers → silver datalake (SCRUM-NEW-04)
**Symptôme** : SSE retourne `"source": "pappers"` (abandonné 2026-04-23). Données pauvres (CA + dirigeants seuls). Risque coût + dépendance hors-roadmap.
**Localisation** :
- `backend/main.py:1604-1650` (SIREN lookup via Pappers MCP dans le copilot)
- `backend/main.py:1631` (`_add_company_to_targets(siren_val)` — side effect)
- `backend/main.py:1445` (message hardcodé "*Entreprise ajoutée à la base EdRCF*")
- `backend/main.py:1451` (fin SSE avec `"source": "pappers"`)
- `backend/pappers_loader.py:842-923` (load pipeline Pappers — TOUT déprécier)
- `backend/clients/deepseek.py:148-158` (tool `get_fiche_entreprise`)
- `backend/routers/datalake.py:289-763` (`_fiche_entreprise_uncached()` — DÉJÀ branché silver)

**Patch** :
1. Dans `main.py:1604-1650`, remplacer l'appel Pappers MCP par un fetch local `GET /api/datalake/fiche/{siren}`.
2. Si la fiche n'existe pas en silver, retourner un message clair plutôt qu'appeler Pappers en fallback.
3. Marquer `pappers_loader.py` comme deprecated (header `# DEPRECATED 2026-05-01 — voir routers/datalake.py::_fiche_entreprise_uncached`).
4. Supprimer `_add_company_to_targets` du SIREN lookup (split en endpoint dédié `POST /api/targets/save`).
5. Émettre `"source": "silver.inpi_comptes ⨝ silver.inpi_dirigeants"` dans le SSE final.

**Test validation** :
```bash
curl -sN "https://82-165-57-191.sslip.io/api/copilot/stream?q=fiche%20SIREN%20333275774" \
  | grep -E '"source":\s*"silver' && echo PASS || echo FAIL
```

---

## 2. P1 MAJEURS — semaine 1 (jour 4-7)

### P1.1 — Compléter fiche SSE (SCRUM-NEW-05)
**Localisation** : `backend/main.py:1639-1644` (formatage final), `backend/clients/deepseek.py:148-158` (schema tool)
**Patch** : enrichir le payload avec :
- `ebitda_str` depuis `gold.entreprises_master.ebitda_proxy`
- `naf_lib` (libellé) — JOIN sur table NAF référentielle (manquante ? créer `ref.naf_codes`)
- `deal_score` + `tier` depuis `gold.scoring_ma`
- `n_mandats_actifs` depuis `gold.dirigeants_master`
- `effectif_str` depuis `silver.insee_etablissements`

---

### P1.2 — Activer Service Worker en prod + fix shortcuts (SCRUM-NEW-06)
**Localisation** :
- `frontend/next.config.ts:7` (`disable: process.env.NODE_ENV === "development"`)
- `frontend/public/manifest.json:35,40` (shortcuts `/targets`, `/graph`)
- `frontend/src/app/layout.tsx:28` (manifest reference)

**Patch** :
1. Le `disable` est correct (dev = pas de SW pour HMR). Vérifier que la build prod sur IONOS génère bien `public/sw.js` non-vide.
2. Ajouter dans `frontend/src/app/layout.tsx` un script client-side qui appelle `navigator.serviceWorker.register('/sw.js')` au mount (Next 15 + Serwist devrait le faire auto, vérifier).
3. Manifest shortcuts → `/#graph` et `/#chat` (pas `/targets`, `/graph`).

**Test validation** : sur prod, `navigator.serviceWorker.getRegistrations().length > 0` doit être vrai.

---

### P1.3 — OpenSanctions retry/backoff + cache fallback (SCRUM-NEW-07)
**Localisation** : `backend/clients/deepseek.py:682-691` (tool `search_sanctions`)
**Patch** :
```python
# backend/clients/deepseek.py:682-691
async def _search_sanctions_with_retry(params, datalake_base):
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f"{datalake_base}/api/datalake/silver/opensanctions",
                                     params={"q": params.get("query", ""), "limit": params.get("limit", 20)})
                if r.status_code == 200:
                    return r.json()
                if r.status_code == 503 and attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return {"error": f"sanctions service unavailable (HTTP {r.status_code})", "fallback": "use silver.opensanctions cache"}
        except Exception as e:
            if attempt == 2: return {"error": str(e)[:200]}
            await asyncio.sleep(2 ** attempt)
```
Considérer aussi un endpoint `/api/datalake/silver/opensanctions-cached` (Redis 5 min TTL).

---

### P1.4 — Synchroniser CA dashboard ↔ fiche (SCRUM-NEW-08)
**Symptôme** : EQUANS dashboard 285.7 M€ vs fiche 152.4 M€ (-46%) ; ELENGY 201.3 vs 191.8 ; COFIBRED 52.9 vs N/A.
**Localisation** :
- `backend/routers/datalake.py:2023-2133` (`/dashboard` → `_cibles_with_routing()`)
- `backend/routers/datalake.py:2625-2743` (`_cibles_with_routing` + `_cibles_from_gold`)
- `backend/routers/datalake.py:2746-2877` (`_cibles_from_silver` — score capé 95)
- `backend/routers/datalake.py:289-763` (`_fiche_entreprise_uncached()`)

**Cause racine** : `_cibles_from_silver` cap le score à 95 et utilise `LEAST(95, 50+CA/200000)` (proxy). Mais `gold.entreprises_master.ca_latest` peut différer du `silver.inpi_comptes.chiffre_affaires` sur le millésime utilisé.
**Patch** : forcer dashboard ET fiche à passer par `gold.entreprises_master` comme source unique. Dépréquer `_cibles_from_silver`. Si gold pas matérialisé, retourner `null` (pas de fallback bruité).

---

### P1.5 — MAX_ITERATIONS / paralléliser tools (SCRUM-NEW-09)
**Localisation** : `backend/clients/deepseek.py:924` (`MAX_ITERATIONS = 12`)
**Symptôme** : 8 / 100 questions complexes → "Plafond d'itérations atteint". Latence p95 = 117s.
**Patch** :
1. Bumper `MAX_ITERATIONS` de 12 → 20 (mais coût LLM ↑).
2. Mieux : exécuter les `tool_calls` en parallèle (`asyncio.gather`) au lieu de séquentiel ligne 951-967.
```python
# backend/clients/deepseek.py:951-967 (refacto)
if tool_calls:
    messages.append(msg)
    results = await asyncio.gather(*[
        _execute_tool(tc["function"]["name"], json.loads(tc["function"]["arguments"]), datalake_base)
        for tc in tool_calls
    ])
    for tc, result in zip(tool_calls, results):
        ... append tool message ...
    continue
```

---

### P1.6 — Fix `search_signaux_bodacc` filtre dept (SCRUM-NEW-10)
**Localisation** : `backend/clients/deepseek.py:285-297` (signature tool), `backend/clients/deepseek.py:693-702` (impl)
**Patch** :
```python
# Ligne 693-702 (à refaire)
async def _search_signaux_bodacc(params, datalake_base):
    q_params = {"limit": params.get("limit", 20)}
    if params.get("siren"): q_params["siren"] = params["siren"]
    if params.get("dept"): q_params["dept"] = params["dept"]      # AJOUT
    if params.get("type_avis"): q_params["type_avis"] = params["type_avis"]  # AJOUT
    if params.get("days"): q_params["days"] = params["days"]      # AJOUT (filtre temporel)
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{datalake_base}/api/datalake/silver/bodacc_annonces", params=q_params)
        return r.json()
```
Vérifier que `routers/datalake.py::query_table` accepte ces filtres en query string (sinon ajouter middleware WHERE clause).

---

### P1.7 — Confirmation explicite avant ajout cible (SCRUM-NEW-11)
**Localisation** : `backend/main.py:1631` (`_add_company_to_targets(siren_val)` silencieux)
**Patch** : retirer le call automatique du SIREN lookup. Le frontend a déjà un bouton "Sauver" sur les cards (cf rapport audit `dem-card-save-btn`). Pas de side effect serveur sur read-only fiche query.

---

## 3. P2 MOYENS — semaine 2 (jour 8-10)

### P2.1 — CTAs contextuels (SCRUM-NEW-12)
**Localisation** : `frontend/src/components/dem/ChatPanel.tsx:488-500`
**Patch** : conditionner `quickReplies` sur `cibles.length > 3` ET `kind === "sourcing"`. Sur questions définitionnelles, mettre `quickReplies: []`.

### P2.2 — Reset state sur "Nouvelle conversation" (SCRUM-NEW-13)
**Localisation** : `frontend/src/components/dem/ChatPanel.tsx:243-254` (`newConversation()`), `26-39` (`initialMessage`)
**Patch** : faire de `initialMessage` une fonction `getInitialMessage(cards)` au lieu d'un objet partagé, qui retourne un nouvel objet à chaque call. Vérifier que `setActiveId(conv.id)` se propage avant le render.

### P2.3 — Format Md€/M€/€ humain dans Explorer (SCRUM-NEW-14)
**Localisation** : composant `dem/ExplorerView.tsx` ou équivalent
**Patch** : utiliser `Intl.NumberFormat('fr-FR', { notation: 'compact', maximumFractionDigits: 1 })` ou helper `formatEur(n)` central.

### P2.4 — Optimiser worker BODACC (SCRUM-NEW-15)
**Localisation** : `infrastructure/agents/platform/ingestion/sources/bodacc.py:44-100`
**Patch** :
1. Utiliser `asyncpg.Connection.copy_records_to_table()` (PostgreSQL COPY natif) au lieu de boucle INSERT.
2. Bumper `BULK_BATCH_SIZE` de 1000 → 10000.
3. Ajouter `MAX_ROWS_PER_RUN = 500_000` pour cap (à l'image de opensanctions ligne 24).

### P2.5 — Reset visuel chat brief (cf P2.2) — SCRUM-NEW-13

### P2.6-P2.8 — sources affichées hardcoded, latence générale, side effect message
Inclus dans P0.4 + P1.5.

---

## 4. P3 MINEURS — semaine 2-3

### P3.1 — Fix `hatvp_lobbying` rows -1 (SCRUM-NEW-16)
**Localisation** : `backend/routers/datalake.py:121-127` (`list_tables()`)
**Patch** : remplacer `reltuples::bigint` par `GREATEST(0, reltuples::bigint)` (idem ligne 93 dans `introspect()`).

### P3.2 — Console error "Uncaught (in promise)"
**Localisation** : `frontend/src/components/dem/ChatPanel.tsx` (probable `await fetch` non catché au mount)
**Patch** : ajouter `.catch(err => console.warn("...", err))` sur les fetch silencieux.

### P3.3 — Conversation `AAAAAAAA…` (test data)
**Localisation** : localStorage `dem.conversations` côté client OU table backend
**Patch** : nettoyer le localStorage demo (purge sur Anne Dupont seed).

### P3.4 — `Effectif: —` partout
**Localisation** : `backend/main.py:1639` (formatage card), `backend/routers/datalake.py::_fiche_entreprise_uncached()`
**Patch** : JOIN avec `silver.insee_etablissements.tranche_effectif` pour récupérer la tranche INSEE (1-9, 10-49, 50-99, etc.).

---

## 5. ORDRE D'EXÉCUTION (rythme prod)

### Sprint A (jours 1-3) — P0 Critiques
| Jour | Tâche                                | Tickets             | Validation                       |
|------|--------------------------------------|---------------------|----------------------------------|
| J1   | P0.1 hallucination DL{N}             | SCRUM-NEW-01        | curl test 6 cas confirmés        |
| J1   | P0.3 hash routing #graphe/#comparer  | SCRUM-NEW-03        | nav 8/8 fonctionnelle            |
| J2-3 | P0.2 fix SSE race                    | SCRUM-NEW-02        | 10 Q en 20s → 10 blocs DOM       |
| J3   | P0.4 migrate Pappers → silver        | SCRUM-NEW-04        | curl source=silver.* sur 5 SIREN |

### Sprint B (jours 4-7) — P1 Majeurs
| J4   | P1.6 fix bodacc filtres + P1.5 parallel tools | SCRUM-NEW-10, NEW-09 | curl bodacc?dept=13              |
| J5   | P1.1 fiche complète (EBITDA + score)          | SCRUM-NEW-05         | fiche SIREN 333275774 a 6 fields |
| J5   | P1.7 retirer side effect targets              | SCRUM-NEW-11         | curl read-only fiche             |
| J6   | P1.4 sync dashboard ↔ fiche                   | SCRUM-NEW-08         | EQUANS CA cohérent partout       |
| J6   | P1.3 OpenSanctions retry                      | SCRUM-NEW-07         | 503 simulé → fallback            |
| J7   | P1.2 PWA service worker                       | SCRUM-NEW-06         | navigator.SW.regs > 0            |

### Sprint C (jours 8-10) — P2 Moyens
| J8  | P2.1 CTAs contextuels                  | SCRUM-NEW-12  |
| J8  | P2.2 reset chat state                  | SCRUM-NEW-13  |
| J9  | P2.3 format €/M€ Explorer              | SCRUM-NEW-14  |
| J9-10 | P2.4 worker BODACC COPY              | SCRUM-NEW-15  |

### Sprint D (jour 11-12) — P3 Mineurs
| J11 | P3.1 hatvp -1 + P3.2 console err + P3.3 + P3.4 | SCRUM-NEW-16 |
| J12 | Re-run AUDIT QA pour vérifier 0 régression     | —            |

---

## 6. PROCESS PR + ATLASSIAN

Pour chaque ticket :

1. **Branche** : `git checkout -b fix/SCRUM-NEW-NN-short-desc`
2. **Commit message** : `fix(domain): description courte (SCRUM-NEW-NN)` — référence ticket dans le body
3. **PR** : titre = ticket Jira, description = before/after + test validation
4. **Atlassian sync** (via agent `atlassian-sync`) :
   - Transition Jira `To Do` → `In Progress` au commit 1
   - Transition `In Progress` → `Done` au merge
   - Ajout commentaire avec lien commit + résultat test
5. **Confluence** : à la fin du sprint, mettre à jour pages 5.2, 5.4, 7.6 + créer 7.7 (audit QA)

---

## 7. TESTS DE NON-RÉGRESSION

À ajouter avant merge final dans `frontend/tests/` et `backend/tests/` :

```typescript
// frontend/tests/chat-no-loss.spec.ts
test('5 messages consécutifs rendent 5 blocs <summary>', async ({ page }) => {
  await page.goto('/#chat');
  for (let i = 0; i < 5; i++) {
    await page.fill('input[placeholder*="Pose"]', `Test ${i}`);
    await page.click('button:has-text("Send")');
    await page.waitForFunction(() =>
      document.querySelectorAll('summary').length === i + 1
    );
  }
});
```

```python
# backend/tests/test_no_label_hallucination.py
@pytest.mark.parametrize("label_n", [28, 46, 57, 87, 92, 94])
async def test_label_not_interpreted_as_dept(label_n):
    q = f"DL{label_n} - top 10 NAF 7010Z"
    chunks = []
    async for c in copilot_ai_query_stream_with_tools(q):
        chunks.append(c)
    text = "".join(chunks)
    assert f"département {label_n}" not in text.lower()
    assert f"({label_n})" not in text
```

---

## 8. RISQUES & ROLLBACK

| Risque                                              | Mitigation                                          |
|-----------------------------------------------------|-----------------------------------------------------|
| Migration Pappers casse fiches en cours             | Garder Pappers en fallback 2 semaines via flag env  |
| Parallel tools fait exploser coût LLM               | Monitorer `audit.copilot_invocations` cost/req      |
| Service worker breaks sur ancien navigateur user    | `if ('serviceWorker' in navigator)` guard           |
| Refacto SSE race introduit nouveaux bugs            | Tests Playwright `chat-no-loss.spec.ts` obligatoire |
| Sync dashboard ↔ fiche change scores → user reports | Sprint A merge sur `develop` 48h soak              |

Rollback : tous les patches passent par `develop` → 24h soak → `main` → deploy. Procédure rollback : `git revert <commit>` + `bash deploy.sh` (cf `docs/RUNBOOK_ROLLBACK.md`).

---

## 9. RAPPORT POST-PATCH (J+12)

À publier dans `docs/ETAT_REEL_2026-05-XX.md` (suite logique de `ETAT_REEL_2026-04-30.md`) :
- Liste 25 bugs avec status (résolu / partiel / data-only)
- Diff `summary` count avant/après audit (cible : 110 / 110 OK + p50 < 10 s)
- Métriques opérationnelles (HTTP 200 sur 7 endpoints clés)
- Commits déployés
- Mise à jour Confluence pages référencées en §0

---

**Auteurs plan** : Zakaria + Claude (audit QA basé sur 110 requêtes API datalake + 5 tests UI + traversée 8 sections nav).
**Référence audit** : `C:\Users\zkhch\audit_demoema\AUDIT_QA_RAPPORT.md` + 9 captures PNG + `dl1_response.network-response`.
