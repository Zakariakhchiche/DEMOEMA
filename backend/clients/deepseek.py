"""Client Copilot DeepSeek (avec fallback Vercel AI Gateway).

Extrait de main.py:516-622. Lit les clés via os.getenv (sera migré vers
Pydantic Settings dans une PR séparée).
"""
from __future__ import annotations

import json
import os
from typing import AsyncIterator

import httpx

# Vercel AI Gateway prioritaire (single key, cost tracking, cache, multi-model
# routing) ; DeepSeek direct en fallback.
AI_GATEWAY_API_KEY = os.getenv("AI_GATEWAY_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

_SYSTEM_PROMPT_FULL = (
    "Tu es le Copilot IA d'EdRCF 6.0, plateforme d'origination M&A "
    "pour Edmond de Rothschild Corporate Finance. Reponds en francais, "
    "de maniere concise et professionnelle. Utilise le markdown pour "
    "formater tes reponses (gras, listes, tableaux).\n\n"
    "Tu as acces a deux sources de donnees:\n"
    "1. Base interne EdRCF: cibles pre-scorees avec signaux M&A\n"
    "2. Pappers (open data): donnees legales/financieres de toutes les entreprises francaises\n\n"
    "Quand le contexte contient des 'Donnees Pappers', analyse-les "
    "en croisant avec les criteres EdRCF (age dirigeant, CA, secteur en consolidation, "
    "structure holding, etc.) pour identifier les meilleures opportunites M&A.\n\n"
    "Contexte:\n{context}"
)

_SYSTEM_PROMPT_STREAM = (
    "Tu es le Copilot IA d'EdRCF 6.0, plateforme d'origination M&A. "
    "Reponds en francais, de maniere concise et professionnelle. "
    "Utilise le markdown pour formater tes reponses.\n\n"
    "Contexte:\n{context}"
)


def _resolve_endpoint() -> tuple[str, str, str] | None:
    """Retourne (api_key, base_url, model) ou None si aucune clé configurée."""
    if AI_GATEWAY_API_KEY:
        return (AI_GATEWAY_API_KEY,
                "https://ai-gateway.vercel.sh/v1/chat/completions",
                "deepseek/deepseek-chat")
    if DEEPSEEK_API_KEY:
        return (DEEPSEEK_API_KEY,
                "https://api.deepseek.com/v1/chat/completions",
                "deepseek-chat")
    return None


async def copilot_ai_query(query: str, context: str) -> str | None:
    """Non-streaming chat completion. Retourne le content ou None si fallback rule-based."""
    resolved = _resolve_endpoint()
    if resolved is None:
        return None
    api_key, base_url, model = resolved
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                base_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "temperature": 0.3,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT_FULL.format(context=context)},
                        {"role": "user", "content": query},
                    ],
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            print(f"[DeepSeek] HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"[DeepSeek] Error: {e}")
    return None


async def copilot_ai_query_stream(query: str, context: str) -> AsyncIterator[str]:
    """Streaming version. Yields text chunks."""
    resolved = _resolve_endpoint()
    if resolved is None:
        return
    api_key, base_url, model = resolved
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                base_url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "stream": True,
                    "max_tokens": 1024,
                    "temperature": 0.3,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT_STREAM.format(context=context)},
                        {"role": "user", "content": query},
                    ],
                },
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and "[DONE]" not in line:
                        try:
                            data = json.loads(line[6:])
                            delta = data["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except Exception:
                            pass
    except Exception as e:
        print(f"[Copilot Stream] Error: {e}")


# ========================================================================
# TOOL-CALLING — le LLM peut faire de vrais appels datalake à la demande.
# Format function-calling OpenAI-compatible (DeepSeek le supporte nativement).
# ========================================================================

COPILOT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_cibles",
            "description": "Recherche cibles M&A dans le datalake silver. Filtres optionnels: texte, département, score minimum. Retourne 5-20 cibles avec siren, denomination, NAF, ville, CA, EBITDA.",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Texte recherché (denomination ILIKE) — ex: 'Carrefour', 'tech IDF'"},
                    "dept": {"type": "string", "description": "Code département 2 chiffres ex: '75', '92'"},
                    "min_score": {"type": "integer", "description": "Score M&A minimum 0-100"},
                    "limit": {"type": "integer", "description": "Nombre résultats (default 5, max 20)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fiche_entreprise",
            "description": "Fiche complète entreprise par SIREN: identité (NAF, forme, ville, dept), financiers (CA, EBITDA, capital), 10 dirigeants détaillés, BODACC, sanctions, presse, network.",
            "parameters": {
                "type": "object",
                "properties": {
                    "siren": {"type": "string", "description": "SIREN 9 chiffres (ex: '542051180' pour TotalEnergies)"},
                },
                "required": ["siren"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dirigeant",
            "description": "Profil complet dirigeant: identité INPI (mandats, formes, rôles), patrimoine SCI (capital + valeur bilan), OSINT (LinkedIn, GitHub, Twitter, emails), sanctions personne, DVF zones.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nom": {"type": "string", "description": "Nom de famille en majuscules (ex: 'MIGNON')"},
                    "prenom": {"type": "string", "description": "Prénom en majuscules (ex: 'LAURENT')"},
                    "date_naissance": {"type": "string", "description": "Date naissance YYYY-MM (optionnel, recommandé pour homonymes)"},
                },
                "required": ["nom", "prenom"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scoring_detail",
            "description": "Détail du score M&A 123 signaux × 13 dimensions pour un siren (Action Prioritaire / Qualification / Monitoring / Veille).",
            "parameters": {
                "type": "object",
                "properties": {
                    "siren": {"type": "string", "description": "SIREN 9 chiffres"},
                },
                "required": ["siren"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_sanctions",
            "description": "Recherche dans silver.sanctions consolidée (AMF + OpenSanctions + ICIJ + DGCCRF + CNIL). Match par nom entité ou siren.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {"type": "string", "description": "Nom entité ou personne ex: 'LVMH', 'Poutine'"},
                    "siren": {"type": "string", "description": "SIREN si recherche par société"},
                    "limit": {"type": "integer", "description": "Default 10"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_signaux_bodacc",
            "description": "Recherche annonces BODACC récentes (cessions, créations holding, procédures collectives, dissolutions). Filtre par siren, département ou type d'avis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "siren": {"type": "string", "description": "SIREN 9 chiffres"},
                    "dept": {"type": "string", "description": "Code département 2 chiffres"},
                    "type_avis": {"type": "string", "description": "Type avis: 'cession', 'creation', 'dissolution', 'procedure_collective'"},
                    "limit": {"type": "integer", "description": "Default 10"},
                },
            },
        },
    },
]


async def _execute_tool(name: str, args: dict, datalake_base: str) -> dict:
    """Execute un tool LLM en appelant l'endpoint interne du datalake."""
    try:
        if name == "search_cibles":
            params = {k: v for k, v in args.items() if v is not None}
            params.setdefault("limit", 5)
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{datalake_base}/api/datalake/cibles", params=params)
                if r.status_code == 200:
                    data = r.json()
                    cibles = data.get("cibles", [])
                    return {"n_cibles": len(cibles), "cibles": [
                        {"siren": c.get("siren"), "denomination": c.get("denomination"),
                         "naf": c.get("naf"), "forme": c.get("forme_juridique"),
                         "ville": c.get("ville"), "dept": c.get("dept"),
                         "ca_dernier": c.get("ca_dernier"), "ebitda_dernier": c.get("ebitda_dernier"),
                         "score_ma": c.get("score_ma"), "marge_pct": c.get("marge_pct")}
                        for c in cibles
                    ]}
                return {"error": f"HTTP {r.status_code}", "cibles": []}

        elif name == "get_fiche_entreprise":
            siren = args.get("siren", "")
            if not siren.isdigit() or len(siren) != 9:
                return {"error": "siren invalide (doit être 9 chiffres)"}
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f"{datalake_base}/api/datalake/fiche/{siren}")
                if r.status_code == 200:
                    d = r.json()
                    f = d.get("fiche") or {}
                    dirigs = (d.get("dirigeants") or [])[:5]
                    return {
                        "fiche": {
                            "siren": f.get("siren"), "denomination": f.get("denomination"),
                            "naf": f.get("naf"), "forme_juridique": f.get("forme_juridique"),
                            "ville": f.get("ville"), "dept": f.get("dept"),
                            "ca_dernier": f.get("ca_dernier"), "ebitda_dernier": f.get("ebitda_dernier"),
                            "capital_social": f.get("capital_social"),
                            "effectif_exact": f.get("effectif_exact"),
                            "annee_creation": f.get("annee_creation"),
                            "n_etablissements": f.get("n_etablissements"),
                            "n_dirigeants": f.get("n_dirigeants"),
                            "statut": f.get("statut"),
                        },
                        "dirigeants": [
                            {"nom": d.get("nom"), "prenom": d.get("prenom"),
                             "age": d.get("age"), "n_mandats_actifs": d.get("n_mandats_actifs"),
                             "is_pro_ma": d.get("is_pro_ma"), "is_senior": d.get("is_senior")}
                            for d in dirigs
                        ],
                        "n_signaux_bodacc": len(d.get("signaux") or []),
                        "n_red_flags": len(d.get("red_flags") or []),
                    }
                return {"error": f"HTTP {r.status_code}"}

        elif name == "get_dirigeant":
            nom = (args.get("nom") or "").upper()
            prenom = (args.get("prenom") or "").upper()
            dn = args.get("date_naissance") or ""
            if not nom or not prenom:
                return {"error": "nom + prenom requis"}
            url = f"{datalake_base}/api/datalake/dirigeant/{nom}/{prenom}"
            if dn:
                url += f"/{dn}"
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(url)
                if r.status_code == 200:
                    return r.json()
                return {"error": f"HTTP {r.status_code}"}

        elif name == "get_scoring_detail":
            siren = args.get("siren", "")
            if not siren.isdigit() or len(siren) != 9:
                return {"error": "siren invalide"}
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{datalake_base}/api/datalake/scoring/{siren}")
                if r.status_code == 200:
                    return r.json()
                return {"error": f"HTTP {r.status_code} (gold.scoring_ma pas matérialisée)"}

        elif name == "search_sanctions":
            params = {"limit": args.get("limit", 10)}
            if args.get("entity_name"):
                params["search"] = args["entity_name"]
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{datalake_base}/api/datalake/silver/sanctions", params=params)
                if r.status_code == 200:
                    data = r.json()
                    return {"n_sanctions": len(data.get("rows", [])), "sanctions": data.get("rows", [])[:10]}
                return {"error": f"HTTP {r.status_code}", "sanctions": []}

        elif name == "search_signaux_bodacc":
            params = {"limit": args.get("limit", 10)}
            if args.get("siren"):
                params["search"] = args["siren"]
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{datalake_base}/api/datalake/silver/bodacc_annonces", params=params)
                if r.status_code == 200:
                    data = r.json()
                    return {"n_signaux": len(data.get("rows", [])), "signaux": data.get("rows", [])[:10]}
                return {"error": f"HTTP {r.status_code}", "signaux": []}

        return {"error": f"Tool {name} inconnu"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


_SYSTEM_PROMPT_TOOLS = (
    "Tu es le Copilot IA d'EdRCF 6.0, plateforme M&A pour Edmond de Rothschild Corporate Finance.\n"
    "Réponds en français, concis et professionnel, en markdown.\n\n"
    "Tu as accès au datalake DEMOEMA via 6 tools :\n"
    "- search_cibles : recherche cibles M&A par texte/dept/score\n"
    "- get_fiche_entreprise : fiche complète d'une entreprise par SIREN\n"
    "- get_dirigeant : profil dirigeant complet (mandats, SCI, OSINT, sanctions)\n"
    "- get_scoring_detail : score M&A 123 signaux × 13 dimensions\n"
    "- search_sanctions : sanctions consolidées (AMF, OpenSanctions, ICIJ, DGCCRF, CNIL)\n"
    "- search_signaux_bodacc : annonces BODACC (cessions, holdings, procédures)\n\n"
    "**RÈGLE CRITIQUE** : tu DOIS appeler les tools pour répondre. Ne jamais hallucinerR de données.\n"
    "Si on te demande une entreprise (TotalEnergies, Renault, Carrefour...), appelle search_cibles ou get_fiche_entreprise.\n"
    "Si tu ne trouves rien, dis-le clairement plutôt qu'inventer.\n"
)


async def copilot_ai_query_stream_with_tools(
    query: str, datalake_base: str = "http://localhost:8000"
) -> AsyncIterator[str]:
    """Tool-calling loop : LLM appelle des tools datalake jusqu'à ce qu'il
    ait assez d'info pour répondre, puis stream la réponse finale.

    Architecture :
      1. POST DeepSeek avec tools=COPILOT_TOOLS (non-stream pour l'étape tool)
      2. Si la réponse contient tool_calls → exécute chaque tool → ajoute le
         résultat dans messages → re-POST DeepSeek
      3. Loop max 5 itérations (cap budget LLM)
      4. Quand le LLM produit du content sans tool_calls → stream chunk par chunk
    """
    resolved = _resolve_endpoint()
    if resolved is None:
        yield "Erreur : aucune clé DeepSeek/AI Gateway configurée."
        return
    api_key, base_url, model = resolved

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT_TOOLS},
        {"role": "user", "content": query},
    ]

    MAX_ITERATIONS = 5
    for iteration in range(MAX_ITERATIONS):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    base_url,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "max_tokens": 1024,
                        "temperature": 0.3,
                        "messages": messages,
                        "tools": COPILOT_TOOLS,
                        "tool_choice": "auto",
                    },
                )
                if resp.status_code != 200:
                    yield f"\nErreur LLM : HTTP {resp.status_code}"
                    return
                data = resp.json()
                msg = data["choices"][0]["message"]
                tool_calls = msg.get("tool_calls") or []

                # Si le LLM veut appeler des tools → exécute et re-loop
                if tool_calls:
                    messages.append(msg)  # ajoute la réponse assistant avec tool_calls
                    for tc in tool_calls:
                        fn_name = tc["function"]["name"]
                        try:
                            fn_args = json.loads(tc["function"]["arguments"])
                        except json.JSONDecodeError:
                            fn_args = {}
                        result = await _execute_tool(fn_name, fn_args, datalake_base)
                        # Cap résultat à 8000 chars pour ne pas exploser le context
                        result_str = json.dumps(result, ensure_ascii=False)[:8000]
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result_str,
                        })
                    continue  # re-LLM avec les tool results

                # Pas de tool_calls → réponse finale
                content = msg.get("content") or ""
                # Stream artificiellement (chunk par 40 chars pour UX cohérent)
                chunk_size = 40
                for i in range(0, len(content), chunk_size):
                    yield content[i:i + chunk_size]
                return

        except Exception as e:
            yield f"\nErreur tool-calling : {type(e).__name__}: {str(e)[:200]}"
            return

    yield "\n(Max iterations atteint — résultat partiel)"
