# Veille performance LLM — DEMOEMA copilot streaming

**Date** : 2026-05-01
**Cible** : agent M&A streaming FastAPI + DeepSeek + Next.js 15
**Méthodo** : recherche SOTA 2025-2026 + audit du code actuel pour réconcilier

---

## Executive summary

PR #40 audit G1 ("anti-hallucination + parallel tools") avait déjà appliqué les 2 plus gros leviers de la veille (parallel tool calls avec SIREN-aware ordering + SSE buffering hardening). La marge restante est plus serrée que ne le suggère un rapport théorique : **20-30% TTFT** réaliste, pas 50-85%.

**Top 3 actions ROI** restant à faire :
1. **Logging `prompt_cache_hit_tokens` DeepSeek** (30min) — mesurer baseline avant d'optimiser à l'aveugle.
2. **Cloudflare AI Gateway** devant DeepSeek (2h) — gratuit, juste base_url change. Cache exact match + observabilité.
3. **Compaction prompts + lazy tools** (4h) — charger `datalake_query` tool seulement si query le justifie.

**Avant tout autre travail** : instrumenter la baseline. Sinon on optimise dans le vide.

---

## Réconciliation rapport théorique vs code actuel

| Reco recensée | Statut réel sur main | Référence code |
|---|---|---|
| Parallel tool calls (`asyncio.gather`) | ✅ **Déjà fait, encore mieux** : SIREN-aware ordering qui groupe les tools du même siren en séquentiel et parallélise les groupes différents | `backend/clients/deepseek.py:1015` (PR #40) |
| SSE buffering hardening (`X-Accel-Buffering: no`) | ✅ **Déjà fait** | `backend/main.py:1600` |
| Ordre messages (`system → user`) | ✅ Correct pour cache hit DeepSeek | `backend/clients/deepseek.py:949-952` |
| Tool dispatcher async | ✅ Implicite via `asyncio.gather` | `deepseek.py:1015` |
| Prompt cache hit logging | ❌ **Pas fait** — aucun tracking `prompt_cache_hit_tokens` | — |
| Cloudflare AI Gateway | ❌ **Pas fait** — appel direct DeepSeek | `_resolve_endpoint()` |
| Speculative tool execution (pre-launch via regex) | ❌ **Pas fait** | — |
| Compaction prompts / lazy tools | ❌ 3 prompts complets chargés à chaque call | — |
| Small-model routing (DeepSeek-Chat → Haiku/Flash) | ❌ Tout DeepSeek | `deepseek.py:_resolve_endpoint` |
| Speculative decoding (Medusa/EAGLE-3) | n/a — DeepSeek API only, pas applicable sauf self-host | — |

---

## Tableau récapitulatif (vrai état post-réconciliation)

| # | Technique | Gain | Qualité | Effort | DEMOEMA | Statut |
|---|-----------|------|---------|--------|---------|--------|
| 1 | Prompt cache hit logging DeepSeek | observabilité | neutre | 30min, 1 | OUI | ❌ TODO |
| 2 | Cloudflare AI Gateway | -90% si hit + obs | neutre | 2h, 2 | OUI | ❌ TODO |
| 3 | Compaction prompts + lazy tools | -10 à -25% TTFT | neutre | 4h, 2 | OUI | ❌ TODO |
| 4 | Speculative tool execution (regex SIREN) | -1 à -3s | neutre si bien fait | 8h, 3 | OUI | ❌ TODO |
| 5 | Small-model routing (DeepSeek + Haiku 4.5) | -1 à -3s TTFT | trade-off contrôlé | 1-2j, 3 | OUI partiel | ❌ TODO |
| 6 | Frontend cold-start Next.js 15 (Edge) | -300-800ms perçu | neutre | 4h, 2 | OUI | À auditer |
| 7 | Pre-fetch heuristics (fiche entreprise) | TTFT perçu = 0 si hit | neutre | 8h, 3 | OUI | ❌ TODO |
| 8 | Parallel tool calls | -30 à -60% multi-tool | neutre | — | OUI | ✅ Déjà fait (#40) |
| 9 | SSE hardening | -200-500ms perçu | neutre | — | OUI | ✅ Déjà fait |

---

## Sections détaillées (vrais leviers restants)

### 1. Prompt cache hit logging DeepSeek — instrumenter avant tout

DeepSeek API retourne dans la response `usage.prompt_cache_hit_tokens` (cache hit) et `usage.prompt_cache_miss_tokens` (cache miss). Aujourd'hui DEMOEMA ne les log pas → on optimise à l'aveugle.

**Action** :
```python
# Dans deepseek.py après resp.json()
data = resp.json()
usage = data.get("usage", {})
hit = usage.get("prompt_cache_hit_tokens", 0)
miss = usage.get("prompt_cache_miss_tokens", 0)
total = hit + miss
hit_rate = hit / total if total else 0
logger.info(f"deepseek.cache_hit_rate={hit_rate:.2%} hit={hit} miss={miss}")
```

**Coût** : 30min. Stockage : étendre la table existante `copilot_logs` avec une colonne JSONB `usage_meta` (cf. mandate "no new tables — enrichir l'existant").

**Impact attendu** : si hit rate déjà > 80% sans rien faire → le cache prompt ne sera pas un grand levier, prioriser ailleurs. Si < 50% → urgent à creuser (peut-être un timestamp dynamique en début de prompt qui casse le cache).

**Source** : https://api-docs.deepseek.com/guides/kv_cache

---

### 2. Cloudflare AI Gateway

Proxy entre FastAPI et DeepSeek qui ajoute :
- Cache exact match natif (clé = hash du payload entier)
- Cache sémantique optionnel (Workers AI embeddings, bêta)
- Observabilité : dashboard requêtes, latence, erreurs, coût
- Retry / fallback / load balancing
- **Gratuit** sur le plan Cloudflare Workers que DEMOEMA a déjà.

**Action** : changer `base_url` dans `_resolve_endpoint()` de `https://api.deepseek.com/v1/chat/completions` vers `https://gateway.ai.cloudflare.com/v1/{ACCOUNT_ID}/{GATEWAY_ID}/deepseek/chat/completions`. Garder l'API key DeepSeek dans Authorization header.

**Effort** : 2h (créer le Gateway dans Cloudflare dashboard + changement code + tests).

**Gain réaliste** :
- Cache hit rate exact-match sur queries M&A : 5-15% (queries trop variées)
- Cache hit rate sur fiches stables (`/fiche/{siren}`) : 30-40%
- Observabilité immédiate de la latence p50/p95/p99 → utile pour mesurer les optimisations futures.

**Trade-off qualité** : `targets_updated_at` ou hash datalake doivent être inclus dans la clé de cache (sinon réponse stale après refresh ETL).

**Source** : https://developers.cloudflare.com/ai-gateway/configuration/caching/

---

### 3. Compaction prompts + lazy tool definitions

Aujourd'hui `_SYSTEM_PROMPT_TOOLS` + `COPILOT_TOOLS` array sont chargés à **chaque** call, même si la query ne nécessite pas tous les tools.

**Actions** :
- **Mesurer** la taille en tokens des 3 prompts via `tiktoken` (ou `len(text)//4` heuristique). Si > 4k tokens chacun → fort potentiel de compaction.
- **Identifier les redondances** entre `_SYSTEM_PROMPT_FULL`, `_SYSTEM_PROMPT_STREAM`, `_SYSTEM_PROMPT_TOOLS`. Si 80% commun → factoriser en un prompt de base + déltas.
- **Lazy tool definitions** : charger seulement les tools probables selon la query :
  - Query contient `\d{9}` → garder `get_pappers_company`, `infogreffe`
  - Query contient `datalake|SQL|agrégat|top` → ajouter `datalake_query`
  - Query courte (< 5 mots) sans verbe d'action → assume "fiche entreprise" → minimal tool set
- Compresser les exemples few-shot si présents (5 → 2).

**Effort** : 4h.

**Gain** : -10 à -25% TTFT en cache miss, neutre en cache hit. Mais surtout **-30 à -50% du coût input tokens** sur les requêtes simples (le tool array prend souvent 1.5-3k tokens).

**Source** : https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents (principe applicable à tous les providers).

---

### 4. Speculative tool execution

Sans attendre le verdict du LLM, **pré-déclencher** les tools probables en parallèle de la première inférence. Pattern : si la query contient un SIREN ou un nom d'entreprise → lancer `get_pappers_company` + `infogreffe` immédiatement.

**Implémentation** :
```python
async def stream_copilot(query: str):
    # 1. Heuristique pré-LLM
    siren_match = re.search(r'\b(\d{9})\b', query)
    speculative_results = {}
    if siren_match:
        siren = siren_match.group(1)
        # Lance les 2 tools les plus fréquemment appelés en parallèle
        speculative_results["pappers"] = asyncio.create_task(get_pappers_company(siren))
        speculative_results["infogreffe"] = asyncio.create_task(get_infogreffe(siren))

    # 2. Démarre l'inférence LLM en parallèle
    llm_task = stream_llm(query)

    # 3. Quand le LLM décide d'appeler un tool, on retourne le résultat speculative si match
    # Sinon, on cancel le speculative et on appelle vraiment.
```

**Effort** : 8h (heuristique + cache + cleanup async).

**Gain** : 1 à 3s par requête sur les patterns matchés (les tools tournent pendant la génération du premier token LLM).

**Risque** : coûts API gaspillés si match rate < 50% (tools déclenchés mais non utilisés). **Métrique à monitorer** : `speculative_hit_rate` = (tools speculatifs utilisés par le LLM / tools speculatifs lancés).

**Source** : pattern décrit dans LangGraph "speculative execution" + paper "PARALLELPROMPT" (arXiv 2506.18728, 2025).

---

### 5. Small-model routing

Router les queries triviales (fiche entreprise, "quel est le CA de X") vers un modèle ~500ms TTFT.

**Modèles ~500ms TTFT 2026** :

| Modèle | TTFT médian | Contexte | Note qualité M&A FR |
|--------|-------------|----------|----------------------|
| Claude Haiku 4.5 | ~400ms | 200k | très bon, tool use solide |
| GPT-4.1-mini | ~500ms | 1M | bon, parallel tools natifs |
| Gemini 2.5 Flash | ~350ms | 1M | excellent ratio prix/vitesse |
| Mistral Small 3.2 (24B) | ~600ms (API) | 128k | correct FR |
| **DeepSeek-Chat** (actuel) | ~1.5-3s | 128k | raisonnement fort |

**Pattern** : un classifier d'intention rapide (regex + heuristiques au début, mini-LLM plus tard) route vers `fast_model` ou `smart_model`. Pour DD compliance / multi-step reasoning → DeepSeek/Sonnet. Pour "donne-moi les dirigeants de SIREN X" → Haiku/Flash.

**Effort** : 1-2 jours (classifier + tests qualité par catégorie).

**Risque** : régression qualité si classifier médiocre. **Garder un fallback** "uncertain → smart model".

**Recommandation DEMOEMA** : commencer avec une heuristique simple (longueur query + mots-clés "stratégie"/"due diligence"/"scoring" → smart, le reste → fast) avant d'investir dans un classifier.

---

### 6. Frontend cold-start Next.js 15 (Edge)

**À auditer** :
- `/api/copilot/stream` est-il sur Edge Runtime Cloudflare Workers ou Node ? Cold-start Node ~300-800ms.
- `streamCopilot()` : utilise `ReadableStream` natif et pas `fetch().json()` (qui attend `done`) ?
- Code splitting : la vue copilot charge ses deps lourds (markdown renderer, syntax highlight) en `React.lazy` ?
- Pre-warm : sur hover du bouton "Copilot", déclencher un HEAD `/api/copilot/stream` pour réveiller le worker ?

**Effort** : 4h audit + fixes éventuels.
**Gain** : -300 à -800ms perçu first interaction.

---

### 7. Pre-fetch heuristics (bonus)

Sur la fiche `/fiche/{siren}`, pré-déclencher en background les 2-3 questions copilot les plus courantes ("quels sont les dirigeants ?", "evolution du CA ?"). Cache 5 min côté frontend.

**Effort** : 8h, complexité 3.
**Gain** : TTFT perçu = 0 si user clique sur la suggestion.
**Risque** : coûts API si peu de hits → mesurer hit rate avant de scaler. Faire seulement si analytics confirme un pattern de questions répétitives.

---

## Plan d'action priorisé (révisé après audit code)

### Semaine 1 — Mesure baseline (1 jour total)

1. **(30min)** Logger `prompt_cache_hit_tokens` DeepSeek dans la table existante `copilot_logs` (colonne JSONB `usage_meta`).
2. **(10min)** Mesurer la taille en tokens des 3 system prompts (`tiktoken`).
3. **(2h)** Cloudflare AI Gateway en place → observabilité immédiate (dashboard latence p50/p95/p99).
4. **(audit 2h)** Vérifier l'Edge Runtime sur `/api/copilot/stream` et le pattern `streamCopilot()` côté Next.js.

→ Total ~1 jour. **À ce stade on a la baseline.** Sans elle, les actions suivantes sont du shotgun.

### Semaine 2 — Optimisation ciblée (2-3 jours)

5. **(4h)** Compaction prompts + lazy tool loading basée sur les mesures de l'étape 2.
6. **(1j)** Speculative tool execution si baseline montre que > 50% des queries déclenchent les mêmes 2-3 tools.
7. **(1j si tout pas fait)** Small-model routing si latence reste un problème — sinon skip.

### Plus tard ou jamais

8. **(2 semaines)** Pre-fetch heuristics — seulement si user analytics confirme des patterns.
9. **(NE PAS FAIRE maintenant)** Self-hosting Mistral/Llama sur Hetzner GPU avec vLLM. Levier énorme (-2 à -5x latence) mais coût opérationnel et qualité < DeepSeek-V3 sur raisonnement M&A. Réévaluer fin 2026.

---

## Méthodologie de mesure (à mettre en place AVANT d'optimiser)

Logger pour chaque requête `/api/copilot/stream` dans `copilot_logs` (colonne JSONB existante) :

```json
{
  "ttft_ms": 1234,
  "total_ms": 4567,
  "prompt_tokens": 2300,
  "prompt_cache_hit_tokens": 1800,
  "completion_tokens": 450,
  "tool_calls_count": 3,
  "tool_calls_total_ms": 1200,
  "tool_calls_max_ms": 800,
  "model_used": "deepseek-chat",
  "iterations": 2
}
```

Métrique principale à suivre : **p95 TTFT** (pas la moyenne). Cible réaliste : 1.5s en p95 pour les queries simples, 4s en p95 pour multi-tool.

---

## Citations / liens

- DeepSeek Context Caching : https://api-docs.deepseek.com/news/news0802
- DeepSeek KV Cache guide : https://api-docs.deepseek.com/guides/kv_cache
- Anthropic prompt caching : https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- OpenAI prompt caching : https://platform.openai.com/docs/guides/prompt-caching
- Gemini context caching : https://ai.google.dev/gemini-api/docs/caching
- Parallel function calling (OpenAI compat) : https://platform.openai.com/docs/guides/function-calling#parallel-function-calling
- Cloudflare AI Gateway caching : https://developers.cloudflare.com/ai-gateway/configuration/caching/
- Helicone semantic cache : https://docs.helicone.ai/features/advanced-usage/caching
- EAGLE-3 paper (mars 2025) : https://arxiv.org/abs/2503.01840
- SGLang RadixAttention : https://lmsys.org/blog/2024-07-25-sglang-llama3/
- Anthropic context engineering 2025 : https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Artificial Analysis benchmarks : https://artificialanalysis.ai/
- PARALLELPROMPT (décomposition prompts) : https://arxiv.org/abs/2506.18728
