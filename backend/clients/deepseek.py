"""Client Copilot DeepSeek (avec fallback Vercel AI Gateway).

Extrait de main.py:516-622. Lit les clés via os.getenv (sera migré vers
Pydantic Settings dans une PR séparée).
"""
from __future__ import annotations

import asyncio
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
            "name": "search_entreprise_by_name",
            "description": (
                "Recherche LARGE d'entreprise par nom — sans filtre M&A, sans "
                "floor CA. Couvre SCIs patrimoniales, holdings, structures non-"
                "cotées (typiquement absentes de search_cibles qui filtre par "
                "CA min 1M€). Source : silver.inpi_comptes denomination ILIKE "
                "+ fallback silver.insee_unites_legales.denomination_unite. "
                "Retourne siren + denomination + ca_dernier (si dispo) + "
                "forme_juridique + etat_administratif. À utiliser en premier "
                "quand l'utilisateur demande 'qui est <nom de société>' ou "
                "'fiche de <nom>' avant de tenter search_cibles. Si trouvé, "
                "enchaîner avec get_fiche_entreprise(siren) pour le détail."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Nom ou fragment de raison sociale (>= 2 chars). Ex: 'ATRIUM PATRIMOINE'"},
                    "limit": {"type": "integer", "description": "Nombre de résultats max (default 10, max 30)"},
                },
                "required": ["q"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dirigeant",
            "description": (
                "Profil complet dirigeant: identité INPI (mandats, formes, rôles), "
                "patrimoine SCI (capital + valeur bilan), OSINT (LinkedIn, GitHub, "
                "Twitter, emails), sanctions personne, DVF zones, ET réseau co-mandats "
                "Neo4j (graph.top_co_mandataires = top 10 associés, "
                "graph.n_red_1hop = nb sanctionnés/offshore/lobbyistes à 1 hop, "
                "graph.is_sanctioned/has_offshore/is_lobbyist = flags compliance). "
                "Utilise pour répondre 'liste les associés de X', 'profil compliance "
                "de X', 'qui dans son réseau direct a un red flag'."
            ),
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
            "description": (
                "Scoring M&A v3 PRO d'une cible — 4 axes business + tier + EV. "
                "Retourne deal_score (0-100), tier (A_HOT/B_WARM/C_PIPELINE/D_WATCH/E_REJECT), "
                "axes {transmission, attractivity, scale, structure} chacun 0-100, "
                "risk multiplier, financials (proxy_ebitda, marge, sector_multiple), "
                "ev_estimated_eur. Utilise pour répondre 'pourquoi cette boîte est-elle "
                "intéressante / pas intéressante en M&A ?'"
            ),
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
            "name": "top_cibles_by_axe",
            "description": (
                "Top N cibles M&A classées par UN axe spécifique du scoring v3 PRO. "
                "Permet de répondre 'top 10 cibles transmission' (dirigeants seniors prêts "
                "à céder), 'top 10 attractivity' (vraie valeur cash), 'top 10 scale' "
                "(taille mid/large cap). Filtre par dept/code_ape/tier optionnel."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "axe": {
                        "type": "string",
                        "enum": ["transmission", "attractivity", "scale", "structure", "deal_score"],
                        "description": "Axe à utiliser pour le tri DESC",
                    },
                    "limit": {"type": "integer", "description": "Default 10, max 50"},
                    "dept": {"type": "string", "description": "Code dept (75, 92, 69, etc.)"},
                    "code_ape": {"type": "string", "description": "Préfixe NAF (62., 71., etc.)"},
                    "tier_min": {
                        "type": "string",
                        "enum": ["A_HOT", "B_WARM", "C_PIPELINE"],
                        "description": "Seuil minimum tier",
                    },
                },
                "required": ["axe"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_scoring",
            "description": (
                "Compare 2 à 5 cibles M&A sur les 4 axes business + EV + tier. "
                "Renvoie une table comparative pour répondre 'compare X vs Y' du point "
                "de vue scoring M&A. Utile pour DD pré-pitch."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sirens": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Liste de 2 à 5 SIRENs à comparer",
                    },
                },
                "required": ["sirens"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "score_breakdown",
            "description": (
                "Décomposition pédagogique du deal_score d'un siren — pourquoi tel score, "
                "axe par axe, avec contexte (âge dirigeant, n_sci, marge, secteur). "
                "Utilisé pour expliquer le résultat à un user qui demande 'pourquoi 65/100 ?'"
            ),
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
    # ====== Tools avancés sourcing ======
    {
        "type": "function",
        "function": {
            "name": "search_dirigeants_60plus",
            "description": "Cherche dirigeants 60+ avec multi-mandats (signal succession M&A imminente). Source silver.inpi_dirigeants (8.1M).",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_mandats": {"type": "integer", "description": "Mandats actifs minimum (default 3)"},
                    "limit": {"type": "integer", "description": "Default 10, max 50"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_sci_patrimoine",
            "description": "Top dirigeants par capital SCI cumulé (fortunes cachées + signal asset-rich). Source silver.dirigeant_sci_patrimoine (3.5M).",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_capital": {"type": "integer", "description": "Capital SCI cumulé minimum en €"},
                    "limit": {"type": "integer", "description": "Default 10"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_co_mandats",
            "description": "Réseau co-mandataires d'une entreprise (qui sont les autres entreprises où ses dirigeants siègent). Pattern key pour M&A relationship mapping.",
            "parameters": {
                "type": "object",
                "properties": {
                    "siren": {"type": "string", "description": "SIREN 9 chiffres"},
                },
                "required": ["siren"],
            },
        },
    },
    # ====== Tools compliance & DD avancée ======
    {
        "type": "function",
        "function": {
            "name": "check_offshore",
            "description": "Match ICIJ Panama/Paradise/Pandora Papers pour un dirigeant ou société. Red flag DD majeur.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Nom personne ou entité"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_lobbying",
            "description": "Inscription HATVP / activité lobbying d'une entreprise (transparence registre français).",
            "parameters": {
                "type": "object",
                "properties": {
                    "siren": {"type": "string", "description": "SIREN 9 chiffres"},
                    "name": {"type": "string", "description": "Nom entreprise (alternatif)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_jurisprudence",
            "description": "Décisions de justice (Cour cassation, Cour appel, Conseil constit, JADE). Source silver.judilibre_decisions (15k).",
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {"type": "string", "description": "Mots-clés (denomination, secteur, type contentieux)"},
                    "limit": {"type": "integer", "description": "Default 10"},
                },
            },
        },
    },
    # ====== Tools marché & éco ======
    {
        "type": "function",
        "function": {
            "name": "search_marches_publics",
            "description": "Marchés publics attribués (BOAMP + DECP). Permet de mesurer dépendance commande publique d'une cible.",
            "parameters": {
                "type": "object",
                "properties": {
                    "siren": {"type": "string", "description": "SIREN du titulaire"},
                    "search": {"type": "string", "description": "Mots-clés (acheteur, secteur)"},
                    "limit": {"type": "integer", "description": "Default 10"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_lei_code",
            "description": "Code LEI international (Legal Entity Identifier) — utile pour cross-border M&A et identification des filiales étrangères.",
            "parameters": {
                "type": "object",
                "properties": {
                    "siren": {"type": "string", "description": "SIREN 9 chiffres"},
                    "name": {"type": "string", "description": "Raison sociale"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_dvf_zones",
            "description": "Transactions immobilières DVF (15M) par code postal ou département. Permet cross-référencer patrimoine immo dirigeants.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code_postal": {"type": "string", "description": "Code postal 5 chiffres"},
                    "min_valeur": {"type": "integer", "description": "Valeur foncière minimum en €"},
                    "limit": {"type": "integer", "description": "Default 10"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_press_recent",
            "description": "Articles de presse récents Google News RSS pour une entreprise. Utilise /api/datalake/fiche qui retourne les 10 derniers articles.",
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
            "name": "get_groupe_filiation",
            "description": "Identifie filiales et maison mère d'une société (structure groupe). Combine GLEIF (parent_lei international) + INPI personnes morales dirigeantes (mères + filiales détectées) + BODACC fusions/absorptions. Indique si la société est une holding ou une filiale.",
            "parameters": {
                "type": "object",
                "properties": {
                    "siren": {"type": "string", "description": "SIREN 9 chiffres"},
                },
                "required": ["siren"],
            },
        },
    },
    # ====== Graph network tools (Neo4j 18.6M nodes + 7.7M CO_MANDATE) =====
    {
        "type": "function",
        "function": {
            "name": "graph_red_flags_network",
            "description": (
                "DD M&A multi-hop : liste les sanctionnés / offshore / lobbyistes "
                "dans le réseau co-mandataires d'un dirigeant à 1, 2 ou 3 hops. "
                "Pour chaque red flag trouvé : nom, distance (hops), type de flag "
                "(sanctioned/offshore/lobbyist), programmes/leaks/lobbies, et un "
                "sample_path qui montre la chaîne de connexion. Utilise pour "
                "'qui dans son entourage a un red flag', 'risques cachés dans le "
                "réseau étendu de X', 'red flags dirigeants à 2 hops'. "
                "Cypher multi-hop sur 7.7M edges — UNIQUEMENT possible via Neo4j, "
                "pas en SQL."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nom": {"type": "string", "description": "Nom de famille en MAJUSCULES (ex: 'ARNAULT')"},
                    "prenom": {"type": "string", "description": "Prénom en MAJUSCULES (ex: 'BERNARD')"},
                    "hops": {"type": "integer", "description": "Profondeur réseau 1-3 (default 2). 1=associés directs uniquement, 2=associés des associés, 3=très étendu."},
                    "limit": {"type": "integer", "description": "Nb max red flags retournés (default 50, max 200)"},
                },
                "required": ["nom", "prenom"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "graph_connection_path",
            "description": (
                "Trouve le chemin le plus court entre 2 personnes via le graphe "
                "des co-mandats. Use case M&A : warm intro mapping ('comment je "
                "passe de X à Y via mes contacts'), investigation network "
                "('comment X est-il connecté à Y'), structure groupe family-office. "
                "Retourne {found: bool, hops: N, persons: [chain]} ou hint si "
                "pas de connexion à profondeur max_hops. Utilise pour 'comment X "
                "est-il connecté à Y', 'qui peut introduire X auprès de Y'. "
                "Shortest path Cypher — IMPOSSIBLE en SQL sur graphe 7.7M edges."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nom_a": {"type": "string", "description": "Nom personne A en MAJUSCULES"},
                    "prenom_a": {"type": "string", "description": "Prénom personne A en MAJUSCULES"},
                    "nom_b": {"type": "string", "description": "Nom personne B en MAJUSCULES"},
                    "prenom_b": {"type": "string", "description": "Prénom personne B en MAJUSCULES"},
                    "max_hops": {"type": "integer", "description": "Profondeur max recherche (default 4, max 6). Plus grand = plus lent mais plus de chances de trouver."},
                },
                "required": ["nom_a", "prenom_a", "nom_b", "prenom_b"],
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

        elif name == "search_entreprise_by_name":
            q = (args.get("q") or "").strip()
            if len(q) < 2:
                return {"error": "q (>= 2 chars) requis"}
            limit = max(1, min(int(args.get("limit", 10)), 30))
<<<<<<< Updated upstream
            # Timeout 30s (vs 12s défaut) : étape 3 silver.inpi_dirigeants
            # peut prendre 8-12s à cold cache (scan arrays denominations[]
            # sans GIN sur ILIKE). Le endpoint lui-même clamp à 10s par step.
=======
            # Timeout 30s : étape 3 silver.inpi_dirigeants + JOIN gold.sci_master
            # peut prendre 8-15s à cold cache (silver-only, no bronze runtime).
>>>>>>> Stashed changes
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{datalake_base}/api/datalake/entreprise/search",
                    params={"q": q, "limit": limit},
                )
                if r.status_code == 200:
                    data = r.json()
                    return {
                        "n": data.get("n", 0),
                        "results": data.get("results", []),
                        "source": "silver.inpi_comptes + silver.insee_unites_legales (sans floor CA)",
                    }
                return {"error": f"HTTP {r.status_code}", "n": 0, "results": []}

        elif name == "get_fiche_entreprise":
            siren = args.get("siren", "")
            if not siren.isdigit() or len(siren) != 9:
                return {"error": "siren invalide (doit être 9 chiffres)"}
            # Timeout 30s : depuis ajout JOIN gold.sci_master en backend
            # 2026-05-03, /fiche/{siren} peut prendre 15-25s à cold cache
            # sur les gros sirens (Carrefour 652014051 = 12 filiales).
            async with httpx.AsyncClient(timeout=30) as client:
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
            # Timeout 30s : sans date_naissance, le silver query parcourt
            # les homonymes et peut prendre 12-25s à cold cache (Vincent
            # LAMOUR 6 homonymes en silver.inpi_dirigeants). Bumpé 15s→30s
            # 2026-05-03 après régression observée en navigateur.
            async with httpx.AsyncClient(timeout=30) as client:
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

        elif name == "top_cibles_by_axe":
            axe = args.get("axe", "deal_score")
            if axe not in ("transmission", "attractivity", "scale", "structure", "deal_score"):
                return {"error": "axe invalide"}
            limit = max(1, min(int(args.get("limit", 10)), 50))
            params = {"limit": limit, "sort": "score_ma"}
            if args.get("dept"):
                params["dept"] = args["dept"]
            if args.get("code_ape"):
                params["naf"] = args["code_ape"]
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{datalake_base}/api/datalake/cibles", params=params)
                if r.status_code != 200:
                    return {"error": f"HTTP {r.status_code}", "cibles": []}
                data = r.json()
                cibles = data.get("cibles", [])
                # Tri client-side par axe (le backend trie par score_ma global)
                axe_col = {"deal_score": "score_ma", "transmission": "transmission_score", "attractivity": "attractivity_score", "scale": "scale_score", "structure": "structure_score"}[axe]
                tier_min = args.get("tier_min")
                if tier_min:
                    tier_order = {"A_HOT": 1, "B_WARM": 2, "C_PIPELINE": 3, "D_WATCH": 4, "E_REJECT": 5}
                    cap = tier_order.get(tier_min, 5)
                    cibles = [c for c in cibles if tier_order.get(c.get("tier") or "E_REJECT", 9) <= cap]
                cibles_sorted = sorted(cibles, key=lambda c: c.get(axe_col) or 0, reverse=True)[:limit]
                return {
                    "axe": axe,
                    "n": len(cibles_sorted),
                    "cibles": [
                        {
                            "siren": c.get("siren"),
                            "denomination": c.get("denomination"),
                            "tier": c.get("tier"),
                            "deal_score": c.get("score_ma"),
                            "transmission": c.get("transmission_score"),
                            "attractivity": c.get("attractivity_score"),
                            "scale": c.get("scale_score"),
                            "structure": c.get("structure_score"),
                            "ev_estimated_eur": c.get("ev_estimated_eur"),
                            "ca_latest": c.get("ca_latest") or c.get("ca_dernier"),
                            "code_ape": c.get("code_ape") or c.get("naf"),
                            "adresse_dept": c.get("adresse_dept") or c.get("siege_dept"),
                        }
                        for c in cibles_sorted
                    ],
                }

        elif name == "compare_scoring":
            sirens = args.get("sirens") or []
            if not isinstance(sirens, list) or len(sirens) < 2 or len(sirens) > 5:
                return {"error": "sirens doit être une liste de 2 à 5 éléments"}
            for s in sirens:
                if not isinstance(s, str) or not s.isdigit() or len(s) != 9:
                    return {"error": f"siren invalide : {s}"}
            results = []
            async with httpx.AsyncClient(timeout=15) as client:
                for siren in sirens:
                    r = await client.get(f"{datalake_base}/api/datalake/scoring/{siren}")
                    if r.status_code == 200:
                        d = r.json()
                        results.append({
                            "siren": siren,
                            "denomination": d.get("denomination"),
                            "tier": d.get("tier"),
                            "deal_score": d.get("deal_score"),
                            "axes": d.get("axes"),
                            "ev_estimated_eur": d.get("financials", {}).get("ev_estimated_eur"),
                            "ca_latest": d.get("financials", {}).get("ca_latest"),
                            "proxy_margin": d.get("financials", {}).get("proxy_margin"),
                            "risk_multiplier": d.get("risk", {}).get("multiplier"),
                        })
                    else:
                        results.append({"siren": siren, "error": f"HTTP {r.status_code}"})
            return {"comparison": results}

        elif name == "score_breakdown":
            siren = args.get("siren", "")
            if not siren.isdigit() or len(siren) != 9:
                return {"error": "siren invalide"}
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{datalake_base}/api/datalake/scoring/{siren}")
                if r.status_code != 200:
                    return {"error": f"HTTP {r.status_code}"}
                d = r.json()
                axes = d.get("axes") or {}
                ctx = d.get("context") or {}
                fin = d.get("financials") or {}
                risk = d.get("risk") or {}
                # Reasoning pédagogique
                reasoning = []
                # Transmission
                t = axes.get("transmission") or 0
                age = ctx.get("age_dirigeant_max")
                n_sci = ctx.get("n_sci_dirigeants") or 0
                if t >= 70:
                    reasoning.append(f"TRANSMISSION FORTE ({t}/100) : dirigeant {age} ans + {n_sci} SCI patrimoniales = transmission imminente probable.")
                elif t >= 40:
                    reasoning.append(f"TRANSMISSION MOYEN ({t}/100) : dirigeant {age} ans, signal de cession modéré.")
                else:
                    reasoning.append(f"TRANSMISSION FAIBLE ({t}/100) : dirigeant trop jeune ou pas de signaux patrimoniaux.")
                # Attractivity
                a = axes.get("attractivity") or 0
                margin = fin.get("proxy_margin")
                ape = ctx.get("code_ape") or "?"
                if a >= 60:
                    reasoning.append(f"ATTRACTIVITY FORTE ({a}/100) : marge proxy {round((margin or 0)*100, 1)}% sur secteur {ape} (multiple {fin.get('sector_multiple')}×).")
                else:
                    reasoning.append(f"ATTRACTIVITY FAIBLE ({a}/100) : marge proxy {round((margin or 0)*100, 1)}%, pas assez profitable pour un acquéreur.")
                # Scale
                s = axes.get("scale") or 0
                ca = fin.get("ca_latest")
                if s >= 70:
                    reasoning.append(f"SCALE FORTE ({s}/100) : CA {round((ca or 0)/1e6, 1)}M€ — mid/large cap, intéresse advisors.")
                elif s >= 35:
                    reasoning.append(f"SCALE MOYEN ({s}/100) : CA {round((ca or 0)/1e6, 1)}M€ — small cap, faisable mais ROI advisor limité.")
                else:
                    reasoning.append(f"SCALE FAIBLE ({s}/100) : CA {round((ca or 0)/1e6, 1)}M€ — sous le seuil 5M€, pas éligible advisor classique.")
                # Risk
                if risk.get("multiplier", 1.0) < 1.0:
                    pen = round((1 - risk.get("multiplier", 1.0)) * 100)
                    reasoning.append(f"RISK -{pen}% : sanctions={risk.get('has_sanction_cnil') or risk.get('has_sanction_dgccrf')} contentieux={risk.get('n_contentieux_recent', 0)} late_filing={risk.get('has_late_filing')}.")
                # EV
                ev = fin.get("ev_estimated_eur")
                if ev:
                    reasoning.append(f"VALORISATION INDICATIVE : {round(ev/1e6, 1)}M€ EUR (proxy_ebitda × multiple sectoriel × scale_premium).")
                return {
                    "siren": siren,
                    "denomination": d.get("denomination"),
                    "tier": d.get("tier"),
                    "deal_score": d.get("deal_score"),
                    "deal_percentile": d.get("deal_percentile"),
                    "axes": axes,
                    "context_summary": {
                        "age_dirigeant_max": age,
                        "n_sci_dirigeants": n_sci,
                        "ca_latest_eur": ca,
                        "code_ape": ape,
                        "sector_multiple": fin.get("sector_multiple"),
                        "ev_estimated_eur": ev,
                    },
                    "reasoning": reasoning,
                }

        elif name == "search_sanctions":
            # Audit QA 2026-05-01 : OpenSanctions API retournait 503 sur 3% des
            # questions compliance, sans fallback → degraded UX. Patch :
            # retry exponentiel 3 tentatives + fallback direct silver.opensanctions
            # (280k rows déjà chargées dans le datalake) avec flag `degraded:true`
            # pour que le LLM mentionne le mode dégradé au user.
            params = {"limit": args.get("limit", 10)}
            if args.get("entity_name"):
                params["search"] = args["entity_name"]

            # Retry primary endpoint (silver.sanctions = vue consolidée AMF/ICIJ/etc)
            last_status: int | None = None
            for attempt in range(3):
                try:
                    async with httpx.AsyncClient(timeout=15) as client:
                        r = await client.get(f"{datalake_base}/api/datalake/silver/sanctions", params=params)
                        last_status = r.status_code
                        if r.status_code == 200:
                            data = r.json()
                            return {
                                "n_sanctions": len(data.get("rows", [])),
                                "sanctions": data.get("rows", [])[:10],
                                "source": "silver.sanctions",
                            }
                        if r.status_code in (502, 503, 504) and attempt < 2:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        break  # 4xx ou erreur définitive → tente fallback
                except (httpx.TimeoutException, httpx.ConnectError):
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    break

            # Fallback : interroger silver.opensanctions directement
            # (sous-ensemble, mais 280k rows = couvre l'essentiel des sanctions UE/OFAC)
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    r = await client.get(
                        f"{datalake_base}/api/datalake/silver/opensanctions",
                        params=params,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        return {
                            "n_sanctions": len(data.get("rows", [])),
                            "sanctions": data.get("rows", [])[:10],
                            "source": "silver.opensanctions",
                            "degraded": True,
                            "degraded_reason": f"silver.sanctions HTTP {last_status} — fallback OpenSanctions cache (280k rows)",
                        }
            except Exception:
                pass

            return {
                "error": f"HTTP {last_status} (sanctions service unavailable, no fallback rows)",
                "sanctions": [],
                "degraded": True,
            }

        elif name == "search_signaux_bodacc":
            params: dict = {"limit": args.get("limit", 10)}
            # Filtres composables (audit QA 2026-05-01: les params dept/type_avis/days
            # étaient déclarés dans la signature LLM mais ignorés côté impl → faux positifs).
            filters = []
            if args.get("siren"):
                filters.append(f"siren.eq.{args['siren']}")
            if args.get("dept"):
                # zfill pour normaliser "1" → "01" car colonne BODACC stocke à 2 digits
                filters.append(f"dept.eq.{str(args['dept']).zfill(2)}")
            if args.get("type_avis"):
                filters.append(f"type_avis.eq.{args['type_avis']}")
            if args.get("days"):
                try:
                    n_days = int(args["days"])
                    filters.append(f"date_publication.gte.now()-interval'{n_days}days'")
                except (TypeError, ValueError):
                    pass
            if filters:
                params["filter"] = ",".join(filters)
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{datalake_base}/api/datalake/silver/bodacc_annonces", params=params)
                if r.status_code == 200:
                    data = r.json()
                    rows = data.get("rows", [])
                    return {
                        "n_signaux": len(rows),
                        "signaux": rows[:10],
                        "filters_applied": filters or ["(aucun, top {} dernières)".format(params["limit"])],
                    }
                return {"error": f"HTTP {r.status_code}", "signaux": [], "filters_applied": filters}

        # ====== Sourcing avancé ======
        elif name == "search_dirigeants_60plus":
            min_mandats = args.get("min_mandats", 3)
            limit = min(args.get("limit", 10), 50)
            params = {"limit": limit, "order": "-n_mandats_actifs",
                      "filter": f"age_2026.gte.60,n_mandats_actifs.gte.{min_mandats}"}
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{datalake_base}/api/datalake/silver/inpi_dirigeants", params=params)
                if r.status_code == 200:
                    rows = r.json().get("rows", [])
                    return {"n": len(rows), "dirigeants": [
                        {k: v for k, v in d.items() if k in ("nom", "prenom", "age_2026",
                                                              "n_mandats_actifs", "n_sci",
                                                              "total_capital_sci")}
                        for d in rows[:20]
                    ]}
                return {"error": f"HTTP {r.status_code}"}

        elif name == "search_sci_patrimoine":
            min_capital = args.get("min_capital", 500000)
            limit = min(args.get("limit", 10), 50)
            params = {"limit": limit, "order": "-total_capital_sci",
                      "filter": f"total_capital_sci.gte.{min_capital}"}
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{datalake_base}/api/datalake/silver/dirigeant_sci_patrimoine", params=params)
                if r.status_code == 200:
                    rows = r.json().get("rows", [])
                    return {"n": len(rows), "dirigeants_top_patrimoine": rows[:20]}
                return {"error": f"HTTP {r.status_code}"}

        elif name == "get_co_mandats":
            siren = args.get("siren", "")
            if not siren.isdigit() or len(siren) != 9:
                return {"error": "siren invalide"}
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f"{datalake_base}/api/datalake/co-mandats/{siren}")
                if r.status_code == 200:
                    return r.json()
                return {"error": f"HTTP {r.status_code}"}

        # ====== Compliance & DD avancée ======
        elif name == "check_offshore":
            search_name = args.get("name", "")
            if not search_name:
                return {"error": "name requis"}
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"{datalake_base}/api/datalake/silver/icij_offshore_match",
                    params={"q": search_name, "limit": 10},
                )
                if r.status_code == 200:
                    rows = r.json().get("rows", [])
                    return {"offshore_match": len(rows) > 0, "n_matches": len(rows), "details": rows[:5]}
                return {"error": f"HTTP {r.status_code} (silver.icij_offshore_match peut etre absent)"}

        elif name == "check_lobbying":
            siren = args.get("siren", "")
            search_name = args.get("name", "")
            params = {"limit": 5}
            if siren:
                params["search"] = siren
            elif search_name:
                params["q"] = search_name
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"{datalake_base}/api/datalake/silver/hatvp_conflits_interets",
                    params=params,
                )
                if r.status_code == 200:
                    rows = r.json().get("rows", [])
                    return {"is_lobbying_registered": len(rows) > 0, "n": len(rows), "details": rows[:5]}
                return {"error": f"HTTP {r.status_code}"}

        elif name == "search_jurisprudence":
            search = args.get("search", "")
            params = {"limit": args.get("limit", 10)}
            if search:
                params["q"] = search
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{datalake_base}/api/datalake/silver/judilibre_decisions", params=params)
                if r.status_code == 200:
                    rows = r.json().get("rows", [])
                    return {"n": len(rows), "decisions": rows[:10]}
                return {"error": f"HTTP {r.status_code}"}

        # ====== Marché & éco ======
        elif name == "search_marches_publics":
            siren = args.get("siren", "")
            search = args.get("search", "")
            params = {"limit": args.get("limit", 10)}
            if siren:
                params["search"] = siren
            elif search:
                params["q"] = search
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{datalake_base}/api/datalake/silver/marches_publics_unifies", params=params)
                if r.status_code == 200:
                    rows = r.json().get("rows", [])
                    return {"n": len(rows), "marches": rows[:10]}
                return {"error": f"HTTP {r.status_code}"}

        elif name == "get_lei_code":
            siren = args.get("siren", "")
            search_name = args.get("name", "")
            params = {"limit": 3}
            if siren:
                params["search"] = siren
            elif search_name:
                params["q"] = search_name
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{datalake_base}/api/datalake/silver/gleif_lei", params=params)
                if r.status_code == 200:
                    rows = r.json().get("rows", [])
                    return {"n": len(rows), "lei": rows[:3]}
                return {"error": f"HTTP {r.status_code}"}

        elif name == "search_dvf_zones":
            cp = args.get("code_postal", "")
            min_valeur = args.get("min_valeur", 500000)
            limit = args.get("limit", 10)
            params = {"limit": limit, "order": "-valeur_fonciere"}
            if cp:
                params["search"] = cp
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{datalake_base}/api/datalake/silver/dvf_transactions", params=params)
                if r.status_code == 200:
                    rows = r.json().get("rows", [])
                    filtered = [t for t in rows if (t.get("valeur_fonciere") or 0) >= min_valeur][:10]
                    return {"n": len(filtered), "transactions": filtered}
                return {"error": f"HTTP {r.status_code}"}

        elif name == "get_press_recent":
            siren = args.get("siren", "")
            if not siren.isdigit() or len(siren) != 9:
                return {"error": "siren invalide"}
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.get(f"{datalake_base}/api/datalake/fiche/{siren}")
                if r.status_code == 200:
                    presse = (r.json() or {}).get("presse", [])
                    return {"n_articles": len(presse), "articles": [
                        {"title": a.get("title"), "url": a.get("url"),
                         "published_at": a.get("published_at"), "source": a.get("source")}
                        for a in presse[:10]
                    ]}
                return {"error": f"HTTP {r.status_code}"}

        elif name == "get_groupe_filiation":
            siren = args.get("siren", "")
            if not siren.isdigit() or len(siren) != 9:
                return {"error": "siren invalide"}
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f"{datalake_base}/api/datalake/groupe-filiation/{siren}")
                if r.status_code == 200:
                    return r.json()
                return {"error": f"HTTP {r.status_code}"}

        # ====== Neo4j graph tools (multi-hop network) ==================
        elif name == "graph_red_flags_network":
            nom = (args.get("nom") or "").upper()
            prenom = (args.get("prenom") or "").upper()
            if not nom or not prenom:
                return {"error": "nom + prenom requis"}
            params = {
                "hops": min(3, max(1, int(args.get("hops") or 2))),
                "limit": min(200, max(10, int(args.get("limit") or 50))),
            }
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.get(
                    f"{datalake_base}/api/graph/red_flags/{nom}/{prenom}",
                    params=params,
                )
                if r.status_code == 200:
                    return r.json()
                return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}

        elif name == "graph_connection_path":
            nom_a = (args.get("nom_a") or "").upper()
            prenom_a = (args.get("prenom_a") or "").upper()
            nom_b = (args.get("nom_b") or "").upper()
            prenom_b = (args.get("prenom_b") or "").upper()
            if not (nom_a and prenom_a and nom_b and prenom_b):
                return {"error": "(nom_a, prenom_a, nom_b, prenom_b) requis"}
            params = {"max_hops": min(6, max(1, int(args.get("max_hops") or 4)))}
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.get(
                    f"{datalake_base}/api/graph/path/{nom_a}/{prenom_a}/{nom_b}/{prenom_b}",
                    params=params,
                )
                if r.status_code == 200:
                    return r.json()
                return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}

        return {"error": f"Tool {name} inconnu"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:200]}"}


_SYSTEM_PROMPT_TOOLS = (
    "Tu es le Copilot IA d'EdRCF 6.0, plateforme M&A pour Edmond de Rothschild Corporate Finance.\n"
    "Réponds en français, concis et professionnel, en markdown.\n\n"
    "Tu as accès au datalake DEMOEMA (107M rows silver) + Neo4j graphe (18.6M nodes, 7.7M relations CO_MANDATE) via 18 tools :\n"
    "**Identité & sourcing** :\n"
    "- search_entreprise_by_name : recherche LARGE par dénomination (sans floor CA, couvre SCIs/holdings/structures non-cotées)\n"
    "- search_cibles : cibles M&A par texte/dept/score (filtre CA ≥ 1M€)\n"
    "- get_fiche_entreprise : fiche complète par SIREN\n"
    "- search_dirigeants_60plus : dirigeants 60+ multi-mandats (succession)\n"
    "- search_sci_patrimoine : top dirigeants par capital SCI cumulé\n"
    "**Dirigeants** :\n"
    "- get_dirigeant : profil complet (mandats, SCI, OSINT, sanctions)\n"
    "- get_co_mandats : réseau co-mandataires d'une entreprise\n"
    "**Scoring M&A** :\n"
    "- get_scoring_detail : score 123 signaux × 13 dimensions\n"
    "**Compliance & DD** :\n"
    "- search_sanctions : sanctions consolidées (AMF/OpenSanctions/ICIJ/DGCCRF/CNIL)\n"
    "- check_offshore : match ICIJ Panama/Paradise Papers\n"
    "- check_lobbying : inscription HATVP / lobbying\n"
    "- search_jurisprudence : décisions de justice\n"
    "**Signaux M&A** :\n"
    "- search_signaux_bodacc : annonces BODACC (cessions/holdings/procédures)\n"
    "- get_press_recent : articles presse récents\n"
    "**Marché & cross-border** :\n"
    "- search_marches_publics : marchés publics gagnés (BOAMP/DECP)\n"
    "- get_lei_code : code LEI international (filiales étrangères)\n"
    "- search_dvf_zones : transactions immobilières par CP/dept\n"
    "**Structure groupe** :\n"
    "- get_groupe_filiation : filiales + maison mère (GLEIF + INPI PM + BODACC fusions)\n"
    "**Network graph (Neo4j multi-hop)** — questions IMPOSSIBLES en SQL :\n"
    "- graph_red_flags_network : sanctionnés/offshore/lobbyistes à 1-3 hops dans le réseau co-mandats d'une personne (DD M&A killer)\n"
    "- graph_connection_path : chemin le plus court entre 2 personnes via co-mandats (warm intro, investigation)\n\n"
    "**RÈGLE ANTI-HALLUCINATION LABELS** : si la query commence par un identifiant interne "
    "(ex: DL12, DL28-, Q5/55, UI3, BUG-42, TEST-7), IGNORE totalement ce label. Ne l'interprète "
    "PAS comme code département FR, code postal, montant, NAF ou tout autre signal métier — "
    "c'est un identifiant de test/audit, jamais une donnée. Concentre-toi uniquement sur le texte "
    "qui suit le label. Exemples : 'DL28 NAF 7010Z' = sourcing NAF 7010Z TOUTES géographies "
    "(PAS département 28 Eure-et-Loir) ; 'Q1/55 fusion vs acquisition' = définition M&A "
    "(PAS sociétés du dept 1 ni T1 2026).\n\n"
    "**RÈGLE CRITIQUE** : tu DOIS appeler les tools pour répondre. Ne jamais halluciner de données.\n"
    "Pour une entreprise : appelle d'abord `search_entreprise_by_name(q=...)` (couverture maximale, "
    "SCIs/holdings/non-cotées incluses), puis `get_fiche_entreprise(siren)` pour le détail. "
    "`search_cibles` est M&A-only (CA ≥ 1M€) — à utiliser quand l'utilisateur demande des cibles "
    "qualifiées (sourcing par secteur/dept/score), pas pour une recherche par nom exact. "
    "Exemple : 'qui est ATRIUM PATRIMOINE' → search_entreprise_by_name(q='ATRIUM PATRIMOINE') "
    "→ get_fiche_entreprise(siren='798303731') ; ne JAMAIS conclure 'pas trouvé' sans avoir "
    "essayé search_entreprise_by_name d'abord.\n"
    "Combine plusieurs tools si pertinent (ex: get_fiche + check_offshore + check_lobbying pour DD).\n"
    "Si tu ne trouves rien, dis-le clairement plutôt qu'inventer.\n"
    "Si un tool retourne `\"degraded\": true` (fallback cache local), mentionne-le explicitement à l'utilisateur.\n"
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

    MAX_ITERATIONS = 20  # bumpé 12→20 (audit QA 2026-05-01: 8% des Q complexes hit le plafond avec 12)
    tool_results_collected: list[dict] = []  # checkpoint : retient les tools réussis pour fallback en synthèse
    for iteration in range(MAX_ITERATIONS):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    base_url,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "max_tokens": 1536,  # élargi pour réponses M&A structurées (tableaux, listes)
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

                    # Parse args + group par SIREN cible commun pour préserver l'ordre causal
                    # (ex: get_fiche puis get_scoring du même SIREN doit rester séquentiel —
                    # les autres tools s'exécutent en parallèle).
                    parsed = []
                    for tc in tool_calls:
                        try:
                            fn_args = json.loads(tc["function"]["arguments"])
                        except json.JSONDecodeError:
                            fn_args = {}
                        parsed.append((tc, tc["function"]["name"], fn_args))

                    # SIREN-aware ordering: tools partageant le même siren restent groupés
                    # et s'exécutent séquentiellement ; les groupes différents en parallèle.
                    by_siren: dict[str, list] = {}
                    standalone: list = []
                    for tc, fn_name, fn_args in parsed:
                        siren = str(fn_args.get("siren") or "").strip()
                        if siren:
                            by_siren.setdefault(siren, []).append((tc, fn_name, fn_args))
                        else:
                            standalone.append((tc, fn_name, fn_args))

                    async def _run_group(group: list) -> list[tuple]:
                        """Exécute séquentiellement un groupe (même siren)."""
                        out = []
                        for tc, fn_name, fn_args in group:
                            r = await _execute_tool(fn_name, fn_args, datalake_base)
                            out.append((tc, fn_name, fn_args, r))
                        return out

                    # Chaque groupe siren = 1 task (séquentielle). Standalone = 1 task chacun (parallèle).
                    coroutines = [_run_group(g) for g in by_siren.values()]
                    coroutines += [_run_group([s]) for s in standalone]
                    results_groups = await asyncio.gather(*coroutines)

                    # Aplatir et préserver l'ordre original des tool_calls
                    flat: dict[str, tuple] = {}  # tool_call_id -> (fn_name, fn_args, result)
                    for grp in results_groups:
                        for tc, fn_name, fn_args, result in grp:
                            flat[tc["id"]] = (fn_name, fn_args, result)
                    for tc in tool_calls:
                        fn_name, fn_args, result = flat[tc["id"]]
                        result_str = json.dumps(result, ensure_ascii=False)[:8000]
                        if not result.get("error"):
                            tool_results_collected.append({"tool": fn_name, "args": fn_args, "result_preview": result_str[:500]})
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

    # Max iterations atteint : au lieu de juste signaler l'échec, on demande au LLM
    # une synthèse forcée des résultats déjà obtenus (sans pouvoir lancer de nouveaux tools).
    if tool_results_collected:
        yield "\n\n*Plafond d'itérations atteint — synthèse des résultats partiels :*\n\n"
        try:
            messages.append({
                "role": "user",
                "content": (
                    "Tu as utilisé tous tes appels d'outils. Sur la base des résultats déjà obtenus dans cette conversation, "
                    "produis MAINTENANT une synthèse Markdown structurée pour répondre à la question initiale, sans appeler "
                    "aucun nouvel outil. Sois concret avec les chiffres disponibles."
                ),
            })
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    base_url,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "max_tokens": 1024,
                        "temperature": 0.3,
                        "messages": messages,
                        # Pas de tools cette fois — on force une réponse texte
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    final_msg = data["choices"][0]["message"].get("content") or ""
                    chunk_size = 40
                    for i in range(0, len(final_msg), chunk_size):
                        yield final_msg[i:i + chunk_size]
                    return
        except Exception as e:
            yield f"\n*Erreur synthèse : {type(e).__name__}*"
            return

    yield "\n(Plafond d'itérations atteint — aucun résultat exploitable. Reformule ta question avec plus de précision : secteur, dépt, tranche CA.)"
