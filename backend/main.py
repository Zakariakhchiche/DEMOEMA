"""
EdRCF 6.0 | AI Origination Intelligence
FastAPI backend for Edmond de Rothschild Corporate Finance M&A platform.
"""

import sys
import os

# Ensure local imports work on Vercel (working dir may not be backend/)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
import asyncio
import copy
import json
from datetime import datetime
import re
import urllib.parse
import xml.etree.ElementTree as ET
import httpx
from dotenv import load_dotenv

load_dotenv()

from demo_data import SIGNAL_CATALOG, DEFAULT_SCORING_WEIGHTS, SECTORS_HEAT
from pappers_loader import load_cache, save_cache, build_target, detect_signals, load_from_supabase, save_to_supabase
from data_sources import (
    get_full_company_info as _papperclip_get_company,
    search_companies_gouv as _papperclip_search,
    load_targets_from_papperclip,
)


# ==========================================================================
# Scoring Engine
# ==========================================================================

scoring_config = copy.deepcopy(DEFAULT_SCORING_WEIGHTS)


def calculate_score(company, weights=None):
    """Calculate score from active signals with dimension capping."""
    if weights is None:
        weights = scoring_config
    dimensions = {k: 0 for k in weights}
    signals_detail = []
    for sig_id in company["active_signals"]:
        sig = SIGNAL_CATALOG.get(sig_id)
        if sig:
            dimensions[sig["dimension"]] += sig["points"]
            signals_detail.append({**sig, "id": sig_id})

    scored = {}
    total = 0
    for dim, raw in dimensions.items():
        mx = weights[dim]["max"]
        capped = min(raw, mx)
        scored[dim] = {
            "score": capped,
            "raw": raw,
            "max": mx,
            "label": weights[dim]["label"],
        }
        total += capped

    if total >= 65:
        priority = "Action Prioritaire"
    elif total >= 45:
        priority = "Qualification"
    elif total >= 25:
        priority = "Monitoring"
    else:
        priority = "Veille Passive"

    return round(total, 1), priority, scored, signals_detail


def enrich_target(company):
    """Apply scoring and return enriched target dict."""
    score, priority, scored_dims, signals = calculate_score(company)
    return {
        **company,
        "globalScore": score,
        "priorityLevel": priority,
        "scoring_details": scored_dims,
        "topSignals": signals,
    }


# Global list populated at startup
enriched_targets = []
_next_idx = 0  # auto-increment index for new targets
# Keep raw targets (pre-enrichment) for re-scoring
raw_targets = []
# Lock to protect concurrent mutations on enriched_targets / raw_targets
_targets_lock = asyncio.Lock()


def _load_targets_sync():
    """Load targets from cache (synchronous, safe for serverless cold start)."""
    global enriched_targets, raw_targets
    if enriched_targets:
        return  # Already loaded
    try:
        cached = load_cache()
        if cached:
            raw_targets = cached
            enriched_targets = [enrich_target(c) for c in cached]
            print(f"[EdRCF] Loaded {len(enriched_targets)} targets from cache")
        else:
            enriched_targets = []
            raw_targets = []
            print("[EdRCF] No cache found. Use /api/refresh-targets to load from Pappers")
    except Exception as e:
        print(f"[EdRCF] Cache load error: {e}")
        enriched_targets = []
        raw_targets = []


@asynccontextmanager
async def lifespan(app):
    global enriched_targets, raw_targets

    # 1. Supabase first — persistent, survives cold starts (fast)
    db_targets = await load_from_supabase()
    if db_targets:
        raw_targets = db_targets
        enriched_targets = [enrich_target(c) for c in db_targets]
        print(f"[EdRCF] Loaded {len(enriched_targets)} targets from Supabase")
    else:
        # 2. Local JSON cache (warm instances only)
        _load_targets_sync()

    # 3. Last resort: fetch companies from free gov APIs (200 target)
    if not enriched_targets:
        try:
            fetched = await load_targets_from_papperclip(count=200)
            if fetched:
                save_cache(fetched)
                await save_to_supabase(fetched)
                raw_targets = fetched
                enriched_targets = [enrich_target(c) for c in fetched]
                print(f"[EdRCF] Loaded {len(enriched_targets)} targets from Papperclip")
        except Exception as e:
            print(f"[EdRCF] Papperclip fetch failed: {e}")

    yield


app = FastAPI(
    title="EdRCF 6.0 | AI Origination Intelligence",
    version="6.0.0",
    lifespan=lifespan,
)

# Structured JSON logging + Prometheus /metrics
try:
    from logging_config import configure_logging, install_prometheus_metrics
    configure_logging()
    install_prometheus_metrics(app)
except Exception as _e:
    import logging as _logging
    _logging.getLogger(__name__).warning("observability setup failed: %s", _e)

# CORS configuration
_default_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
]
_default_origin_regex = r"https://.*\.(vercel\.app|workers\.dev|pages\.dev)$"
_extra_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_origin_regex=os.getenv("CORS_ORIGIN_REGEX", _default_origin_regex),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Admin pipeline router (Bronze/Silver/BODACC/RNE/Pappers)
from routers.admin import router as _admin_router
app.include_router(_admin_router)

# Ensure targets are loaded even if lifespan doesn't run (Vercel serverless)
_load_targets_sync()


@app.get("/api/health")
async def health():
    return {"status": "ok"}


async def _add_company_to_targets(siren: str) -> Optional[dict]:
    """Fetch a company from Pappers, build a target, and add it to enriched_targets.
    Returns the enriched target dict, or None if it fails.
    Thread-safe via _targets_lock."""
    global enriched_targets, raw_targets, _next_idx
    # Quick check outside lock (avoids unnecessary Pappers call)
    existing = next((t for t in enriched_targets if t.get("siren") == siren), None)
    if existing:
        return existing
    try:
        company_info = await get_pappers_company(siren)
        if not company_info or not isinstance(company_info, dict) or "raw" in company_info:
            return None
        async with _targets_lock:
            # Re-check inside lock (another coroutine may have added it)
            existing = next((t for t in enriched_targets if t.get("siren") == siren), None)
            if existing:
                return existing
            _next_idx = max(_next_idx, len(enriched_targets)) + 1
            target = build_target(idx=_next_idx, company_info=company_info, search_info={})
            raw_targets.append(target)
            enriched = enrich_target(target)
            enriched_targets.append(enriched)
            save_cache(raw_targets)
            return enriched
    except Exception as e:
        print(f"[EdRCF] _add_company_to_targets error for {siren}: {e}")
        return None


# ==========================================================================
# Pappers MCP Client
# ==========================================================================


async def search_pappers(query: str = "", par_page: str = "10", **filters):
    """Search companies via Papperclip (free gov APIs). Returns Pappers-compatible structure."""
    # Direct SIREN lookup if query is exactly 9 digits
    clean_query = query.strip()
    if re.match(r'^\d{9}$', clean_query):
        company_info = await _papperclip_get_company(clean_query)
        if company_info and isinstance(company_info, dict) and company_info.get("siren"):
            return {"resultats": [company_info], "total": 1}

    count = min(int(par_page or "10"), 25)
    code_naf = filters.get("code_naf", "")
    departement = filters.get("departement", "")
    # Use nom_entreprise filter if provided, otherwise free text query
    search_query = filters.get("nom_entreprise") or query
    companies = await _papperclip_search(
        query=search_query,
        code_naf=code_naf,
        departement=departement,
        per_page=count,
    )
    return {"resultats": companies, "total": len(companies)}


async def get_pappers_company(siren: str):
    """Get company details via Papperclip (free gov APIs)."""
    return await _papperclip_get_company(siren)


def _extract_group_info(data: dict, cartographie: dict = None) -> dict:
    """
    Extrait les informations groupe/holding/statut depuis les donnees Pappers.
    Utilise informations-entreprise + optionnellement cartographie-entreprise.
    """
    nom = (data.get("nom_entreprise") or "").lower()
    libelle_naf = (data.get("libelle_code_naf") or "").lower()
    code_naf = data.get("code_naf") or ""
    etablissements = data.get("etablissements") or []
    beneficiaires = data.get("beneficiaires_effectifs") or []

    # --- Statut activite ---
    cessee = data.get("entreprise_cessee", False)
    statut = "Radie" if cessee else "En activite"
    date_cessation = data.get("date_cessation")

    # --- Holding (detection par NAF + nom) ---
    is_holding = (
        "holding" in nom
        or "holding" in libelle_naf
        or code_naf.startswith("64.2")
        or code_naf.startswith("64.3")
        or code_naf.startswith("65.23")
    )

    # --- Societe mere via beneficiaires_effectifs (personne morale) ---
    parent = None
    for be in beneficiaires:
        be_type = (be.get("type") or "").lower()
        if "societe" in be_type or "morale" in be_type or "personne morale" in be_type:
            parent = {
                "siren": be.get("siren"),
                "name": be.get("denomination") or be.get("nom"),
                "pourcentage": be.get("pourcentage_parts"),
            }
            break

    # --- Groupe via cartographie-entreprise (si disponible) ---
    entreprises_liees = []
    if cartographie and isinstance(cartographie, dict):
        carto_entreprises = cartographie.get("entreprises") or []
        siren_cible = data.get("siren")
        for e in carto_entreprises:
            if e.get("siren") != siren_cible:
                entreprises_liees.append({
                    "siren": e.get("siren"),
                    "name": e.get("nom_entreprise"),
                })
        if entreprises_liees:
            is_holding = True  # S'il y a des entreprises liées, c'est un groupe

    # --- Etablissements secondaires ---
    secondary_sites = []
    if isinstance(etablissements, list):
        for e in etablissements[1:6]:
            secondary_sites.append({
                "siret": e.get("siret"),
                "ville": e.get("ville"),
                "code_postal": e.get("code_postal"),
                "activite": e.get("libelle_code_naf") or e.get("activite_principale"),
            })

    is_group = is_holding or (parent is not None) or len(etablissements) > 1 or len(entreprises_liees) > 0

    return {
        "statut_activite": statut,
        "date_cessation": date_cessation,
        "is_group": is_group,
        "is_holding": is_holding,
        "parent": parent,
        "entreprises_liees": entreprises_liees,
        "nb_etablissements": len(etablissements),
        "secondary_sites": secondary_sites,
    }


async def get_pappers_dirigeants(siren: str):
    """Get company directors via Papperclip."""
    data = await _papperclip_get_company(siren)
    if not data:
        return None
    return {"representants": data.get("representants", []), "siren": siren,
            "nom_entreprise": data.get("nom_entreprise", "")}


def _validate_siren(siren: str) -> str:
    """Valide et nettoie un SIREN. Leve HTTPException si invalide."""
    siren = siren.strip().replace(" ", "")
    if not siren.isdigit() or len(siren) != 9:
        raise HTTPException(status_code=400, detail="SIREN invalide — doit contenir 9 chiffres")
    return siren


def _parse_mcp_json(result) -> Optional[dict]:
    """Extrait le JSON depuis une reponse MCP (content blocks ou direct)."""
    if not result:
        return None
    if isinstance(result, dict) and "content" in result:
        for block in result["content"]:
            if block.get("type") == "text":
                try:
                    return json.loads(block["text"])
                except json.JSONDecodeError:
                    return {"raw": block["text"]}
    return result if isinstance(result, dict) else None


async def get_pappers_bodacc(siren: str) -> Optional[dict]:
    """Recupere les publications BODACC via Papperclip (incluses dans get_full_company_info)."""
    return await _papperclip_get_company(siren)


async def get_pappers_procedures(siren: str) -> Optional[dict]:
    """Recupere les procedures collectives via Papperclip."""
    return await _papperclip_get_company(siren)


async def get_cartographie(siren: str) -> Optional[dict]:
    """Cartographie groupe non disponible dans Papperclip v1. Returns None."""
    return None


async def get_comptes(siren: str, annee: str = "") -> Optional[dict]:
    """Comptes annuels detailles non disponibles dans Papperclip v1. Returns None."""
    return None


async def search_dirigeant_by_name(q: str) -> Optional[dict]:
    """Recherche dirigeant par nom via Papperclip — recherche approximative par raison sociale."""
    companies = await _papperclip_search(query=q, per_page=20)
    resultats = []
    q_lower = q.lower()
    for company in companies:
        reps = company.get("representants", [])
        matching = [
            r for r in reps
            if q_lower in f"{r.get('prenom', '')} {r.get('nom', '')}".lower()
        ]
        if matching:
            for rep in matching:
                resultats.append({
                    "entreprises": [{
                        "siren": company.get("siren"),
                        "nom_entreprise": company.get("nom_entreprise"),
                        "code_naf": company.get("code_naf"),
                        "libelle_code_naf": company.get("libelle_code_naf"),
                        "siege": company.get("siege"),
                        "dirigeant": {"qualites": [rep.get("qualite", "")], "actuel": True},
                    }]
                })
    return {"resultats": resultats, "total": len(resultats)}


async def get_pappers_concurrents(code_naf: str, departement: str = "", ca_min: int = 0) -> Optional[dict]:
    """Recherche les entreprises concurrentes via Papperclip (meme code NAF, meme departement)."""
    companies = await _papperclip_search(
        code_naf=code_naf,
        departement=departement,
        per_page=20,
    )
    return {"resultats": companies, "total": len(companies)}


# ==========================================================================
# Google News RSS
# ==========================================================================

PRESS_SIGNAL_KEYWORDS = {
    "presse_cession": ["cession", "cede", "cède", "vend", "reprise", "acquis", "acquisition", "rachat", "vendu"],
    "presse_difficultes": ["liquidation", "redressement", "difficulte", "difficultes", "perte", "faillite", "dépôt de bilan"],
    "presse_levee_fonds": ["levée de fonds", "leve", "lèvent", "investissement", "financement", "capital-risque"],
    "presse_partenariat": ["partenariat", "alliance", "accord", "joint-venture", "rapprochement"],
}


async def get_google_news(company_name: str, max_results: int = 6) -> list:
    """Fetch recent news from Google News RSS for a company name."""
    query = urllib.parse.quote(f'"{company_name}"')
    url = f"https://news.google.com/rss/search?q={query}&hl=fr&gl=FR&ceid=FR:fr"
    try:
        async with httpx.AsyncClient(timeout=6, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; EdRCF/6.0)"
            })
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.content)
        channel = root.find("channel")
        if not channel:
            return []
        articles = []
        for item in channel.findall("item")[:max_results]:
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            pub_date = item.findtext("pubDate") or ""
            source = item.findtext("source") or ""
            title_lower = title.lower()
            detected = [
                sig for sig, kws in PRESS_SIGNAL_KEYWORDS.items()
                if any(kw in title_lower for kw in kws)
            ]
            articles.append({
                "title": title,
                "link": link,
                "date": pub_date,
                "source": source,
                "signals": detected,
            })
        return articles
    except Exception as e:
        print(f"[GoogleNews] Error for '{company_name}': {e}")
        return []


# ==========================================================================
# Infogreffe open data
# ==========================================================================

INFOGREFFE_DATASETS = [
    "actes-rcs-insee",
    "kbis-et-actes",
    "actes-et-bilans",
]
INFOGREFFE_BASE = "https://opendata.datainfogreffe.fr/api/explore/v2.1/catalog/datasets"


async def get_infogreffe_actes(siren: str, max_results: int = 10) -> list:
    """
    Fetch recent actes RCS from Infogreffe open data by SIREN.
    Tries multiple dataset names gracefully (3s per dataset, 8s total).
    """
    for dataset in INFOGREFFE_DATASETS:
        url = f"{INFOGREFFE_BASE}/{dataset}/records"
        params = {
            "where": f'siren="{siren}"',
            "limit": max_results,
            "order_by": "date_depot desc",
        }
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                records = data.get("results") or data.get("records") or []
                if records:
                    actes = []
                    for r in records:
                        fields = r.get("fields") or r
                        actes.append({
                            "type": (fields.get("libelle_type_acte")
                                     or fields.get("type_acte")
                                     or fields.get("nature")
                                     or "Acte"),
                            "date": (fields.get("date_depot")
                                     or fields.get("date")
                                     or ""),
                            "description": (fields.get("libelle")
                                            or fields.get("description")
                                            or ""),
                            "siren": siren,
                        })
                    return actes
        except Exception as e:
            print(f"[Infogreffe] Dataset {dataset} error for SIREN {siren}: {e}")
            continue
    return []


# ==========================================================================
# Copilot with DeepSeek AI
# ==========================================================================

# Vercel AI Gateway (prioritaire) ou DeepSeek direct (fallback)
AI_GATEWAY_API_KEY = os.getenv("AI_GATEWAY_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")


async def copilot_ai_query(query: str, context: str):
    # Prefer Vercel AI Gateway — single key, cost tracking, cache, multi-model routing
    if AI_GATEWAY_API_KEY:
        api_key = AI_GATEWAY_API_KEY
        base_url = "https://ai-gateway.vercel.sh/v1/chat/completions"
        model = "deepseek/deepseek-chat"
    elif DEEPSEEK_API_KEY:
        api_key = DEEPSEEK_API_KEY
        base_url = "https://api.deepseek.com/v1/chat/completions"
        model = "deepseek-chat"
    else:
        return None  # Fall back to rule-based
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
                        {
                            "role": "system",
                            "content": (
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
                                f"Contexte:\n{context}"
                            ),
                        },
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


async def copilot_ai_query_stream(query: str, context: str):
    """Streaming version of copilot_ai_query. Yields text chunks."""
    if AI_GATEWAY_API_KEY:
        api_key = AI_GATEWAY_API_KEY
        base_url = "https://ai-gateway.vercel.sh/v1/chat/completions"
        model = "deepseek/deepseek-chat"
    elif DEEPSEEK_API_KEY:
        api_key = DEEPSEEK_API_KEY
        base_url = "https://api.deepseek.com/v1/chat/completions"
        model = "deepseek-chat"
    else:
        return
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
                        {
                            "role": "system",
                            "content": (
                                "Tu es le Copilot IA d'EdRCF 6.0, plateforme d'origination M&A. "
                                "Reponds en francais, de maniere concise et professionnelle. "
                                "Utilise le markdown pour formater tes reponses.\n\n"
                                f"Contexte:\n{context}"
                            ),
                        },
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


# ==========================================================================
# API Endpoints
# ==========================================================================


@app.get("/api/targets")
def get_targets(
    q: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    ebitda_range: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None),
    structure: Optional[str] = Query(None),
    publication_status: Optional[str] = Query(None),
):
    results = enriched_targets
    if q:
        ql = q.lower()
        results = [
            t
            for t in results
            if ql in t["name"].lower()
            or ql in t["sector"].lower()
            or ql in t.get("sub_sector", "").lower()
            or ql in t.get("city", "").lower()
            or ql in t.get("siren", "")
        ]
    if sector:
        results = [t for t in results if t["sector"] == sector]
    if region:
        results = [t for t in results if t["region"] == region]
    if ebitda_range:
        results = [t for t in results if t["financials"]["ebitda_range"] == ebitda_range]
    if min_score is not None:
        results = [t for t in results if t["globalScore"] >= min_score]
    if structure:
        results = [t for t in results if t["structure"] == structure]
    if publication_status:
        results = [t for t in results if t["publication_status"] == publication_status]

    results = sorted(results, key=lambda x: x["globalScore"], reverse=True)
    return {
        "data": results,
        "total": len(results),
        "filters": {
            "sectors": sorted(set(t["sector"] for t in enriched_targets)),
            "regions": sorted(set(t["region"] for t in enriched_targets)),
            "structures": sorted(set(t["structure"] for t in enriched_targets)),
            "ebitda_ranges": ["< 3M", "3-10M", "10-30M", "> 30M"],
        },
    }


@app.get("/api/targets/search-pappers")
async def search_pappers_endpoint(q: str = Query(...)):
    """Search real companies via Pappers MCP, enrich and add to targets."""
    pappers_data = await search_pappers(q)

    if isinstance(pappers_data, dict) and "resultats" in pappers_data:
        companies = []
        # Enrich each result in background — add to enriched_targets
        add_tasks = []
        for r in pappers_data["resultats"][:10]:
            siren = r.get("siren", "")
            company = {
                "siren": siren,
                "name": r.get("nom_entreprise", r.get("denomination", "")),
                "siege": r.get("siege", {}),
                "dirigeants": r.get("representants", []),
                "date_creation": r.get("date_creation", ""),
                "code_naf": r.get("code_naf", ""),
                "libelle_naf": r.get("libelle_code_naf", ""),
                "effectif": r.get("effectif", ""),
                "forme_juridique": r.get("forme_juridique", ""),
                "capital": r.get("capital", ""),
            }
            companies.append(company)
            # Queue enrichment for each company with a SIREN
            if siren:
                add_tasks.append(_add_company_to_targets(siren))

        # Run all enrichments concurrently (best-effort, don't block response)
        if add_tasks:
            await asyncio.gather(*add_tasks, return_exceptions=True)

        return {"data": companies, "total": pappers_data.get("total", 0), "source": "pappers-mcp"}

    return {"data": pappers_data, "source": "pappers-mcp"}


@app.get("/api/pappers/search-edrcf")
async def search_pappers_edrcf(
    code_naf: Optional[str] = Query(None),
    age_dirigeant_min: Optional[str] = Query(None),
    chiffre_affaires_min: Optional[str] = Query(None),
    chiffre_affaires_max: Optional[str] = Query(None),
    departement: Optional[str] = Query(None),
    capital_min: Optional[str] = Query(None),
    par_page: str = Query("10"),
    inclure_radiees: bool = Query(False, description="Inclure les entreprises radiees (defaut: non)"),
):
    """Search Pappers with EdRCF-specific M&A filters."""
    filters = {
        "par_page": par_page,
        "entreprise_cessee": inclure_radiees,
    }
    if code_naf:
        filters["code_naf"] = code_naf
    if age_dirigeant_min:
        filters["age_dirigeant_min"] = age_dirigeant_min
    if chiffre_affaires_min:
        filters["chiffre_affaires_min"] = chiffre_affaires_min
    if chiffre_affaires_max:
        filters["chiffre_affaires_max"] = chiffre_affaires_max
    if departement:
        filters["departement"] = departement
    if capital_min:
        filters["capital_min"] = capital_min

    pappers_data = await search_pappers(**filters)

    if isinstance(pappers_data, dict) and "resultats" in pappers_data:
        companies = []
        for r in pappers_data["resultats"][:int(par_page)]:
            siege = r.get("siege", {}) or {}
            ca = r.get("chiffre_affaires")
            cessee = r.get("entreprise_cessee", False)
            nom = (r.get("nom_entreprise") or "").lower()
            libelle = (r.get("libelle_code_naf") or "").lower()
            code_naf_r = r.get("code_naf") or ""
            is_holding = (
                "holding" in nom
                or "holding" in libelle
                or code_naf_r.startswith("64.2")
                or code_naf_r.startswith("64.3")
            )
            companies.append({
                "siren": r.get("siren", ""),
                "name": r.get("nom_entreprise", ""),
                "city": siege.get("ville", ""),
                "code_postal": siege.get("code_postal", ""),
                "date_creation": r.get("date_creation", ""),
                "code_naf": r.get("code_naf", ""),
                "libelle_naf": r.get("libelle_code_naf", ""),
                "effectif": r.get("effectif", ""),
                "forme_juridique": r.get("forme_juridique", ""),
                "capital": r.get("capital"),
                "chiffre_affaires": ca,
                "chiffre_affaires_fmt": f"{ca/1e6:.1f}M EUR" if ca and ca > 0 else "N/A",
                "resultat": r.get("resultat"),
                "statut_activite": "Radie" if cessee else "En activite",
                "is_holding": is_holding,
            })
        return {"data": companies, "total": pappers_data.get("total", 0), "source": "pappers-mcp"}
    return {"data": pappers_data, "source": "pappers-mcp"}


@app.get("/api/pappers/company/{siren}")
async def get_pappers_company_endpoint(siren: str):
    """Get detailed company info from Pappers MCP."""
    data = await get_pappers_company(siren)
    if data:
        return {"data": data, "source": "pappers-mcp"}
    raise HTTPException(status_code=404, detail="Entreprise non trouvee via Pappers")


@app.get("/api/pappers/dirigeants/{siren}")
async def get_pappers_dirigeants_endpoint(siren: str):
    """Get company directors from Pappers MCP."""
    data = await get_pappers_dirigeants(siren)
    if data:
        return {"data": data, "source": "pappers-mcp"}
    raise HTTPException(status_code=404, detail="Dirigeants non trouves via Pappers")


@app.get("/api/pappers/siren/{siren}")
async def get_company_by_siren(siren: str):
    """
    Recherche une entreprise par son numero SIREN.
    Retourne les informations completes incluant :
    - Statut activite (En activite / Radie)
    - Appartenance a un groupe ou holding
    - Societe mere et actionnaires
    - Etablissements secondaires
    """
    siren = _validate_siren(siren)

    # Appels paralleles : infos generales + cartographie (cartographie peut timeout sur grandes entreprises)
    res = await asyncio.gather(
        get_pappers_company(siren),
        get_cartographie(siren),
        return_exceptions=True,
    )
    data = res[0] if not isinstance(res[0], Exception) else None
    carto = res[1] if not isinstance(res[1], Exception) else None

    if not data or not isinstance(data, dict) or "raw" in data:
        raise HTTPException(status_code=404, detail=f"Entreprise SIREN {siren} non trouvee via Pappers")

    group_info = _extract_group_info(data, carto)
    siege = data.get("siege") or {}
    finances = data.get("finances") or []
    ca = finances[0].get("chiffre_affaires") if finances else None

    return {
        "source": "pappers-mcp",
        "data": {
            "siren": data.get("siren"),
            "nom_entreprise": data.get("nom_entreprise"),
            "forme_juridique": data.get("forme_juridique"),
            "date_creation": data.get("date_creation"),
            "capital": data.get("capital"),
            "code_naf": data.get("code_naf"),
            "libelle_naf": data.get("libelle_code_naf"),
            "effectif": data.get("effectif"),
            "siege": {
                "adresse": siege.get("adresse"),
                "code_postal": siege.get("code_postal"),
                "ville": siege.get("ville"),
                "departement": siege.get("departement"),
            },
            "chiffre_affaires": ca,
            "chiffre_affaires_fmt": f"{ca/1e6:.1f}M EUR" if ca and ca > 0 else "N/A",
            "statut_activite": group_info["statut_activite"],
            "date_cessation": group_info["date_cessation"],
            "procedure_collective_en_cours": data.get("procedure_collective_en_cours", False),
            "groupe": {
                "is_group": group_info["is_group"],
                "is_holding": group_info["is_holding"],
                "societe_mere": group_info["parent"],
                "entreprises_liees": group_info["entreprises_liees"],
                "nb_etablissements": group_info["nb_etablissements"],
                "etablissements_secondaires": group_info["secondary_sites"],
            },
        },
    }


@app.get("/api/pappers/statut/{siren}")
async def get_company_statut(siren: str):
    """
    Verifie rapidement le statut d'activite d'une entreprise (active ou radiee)
    et son appartenance eventuelle a un groupe ou holding.
    """
    siren = siren.strip().replace(" ", "")
    if not siren.isdigit() or len(siren) != 9:
        raise HTTPException(status_code=400, detail="SIREN invalide — doit contenir 9 chiffres")

    data = await get_pappers_company(siren)
    if not data or not isinstance(data, dict) or "raw" in data:
        raise HTTPException(status_code=404, detail=f"Entreprise SIREN {siren} non trouvee via Pappers")

    group_info = _extract_group_info(data)

    return {
        "source": "pappers-mcp",
        "siren": siren,
        "nom_entreprise": data.get("nom_entreprise"),
        "statut_activite": group_info["statut_activite"],
        "date_cessation": group_info["date_cessation"],
        "is_group": group_info["is_group"],
        "is_holding": group_info["is_holding"],
        "societe_mere": group_info["parent"],
        "nb_etablissements": group_info["nb_etablissements"],
    }


@app.get("/api/pappers/bodacc/{siren}")
async def get_bodacc_endpoint(siren: str):
    """
    Publications BODACC d'une entreprise via Pappers MCP.
    Champ reel : publications_bodacc dans informations-entreprise.
    Structure : {type, date, description, administration, bodacc, numero_annonce}
    Types BODACC : Modification, Immatriculation, Vente, Radiation, Depot des comptes...
    """
    siren = _validate_siren(siren)
    data = await get_pappers_bodacc(siren)
    if not data:
        raise HTTPException(status_code=404, detail=f"Entreprise SIREN {siren} non trouvee")

    publications = data.get("publications_bodacc") or []
    if not isinstance(publications, list):
        publications = []

    # Classification basee sur le champ "type" reel de Pappers BODACC
    cessions, capital_changes, dissolutions, transferts, procedures, autres = [], [], [], [], [], []
    for pub in publications:
        type_pub = (pub.get("type") or "").lower()
        desc = (pub.get("description") or "").lower()
        admin = (pub.get("administration") or "").lower()
        combined = f"{type_pub} {desc} {admin}"
        entry = {
            "date": pub.get("date"),
            "type": pub.get("type") or "Autre",
            "numero_annonce": pub.get("numero_annonce"),
            "bodacc": pub.get("bodacc"),
            "description": pub.get("description") or pub.get("administration") or "",
            "greffe": pub.get("greffe"),
        }
        if any(w in combined for w in ["vente", "cession", "cession de fonds"]):
            cessions.append(entry)
        elif any(w in combined for w in ["capital", "augmentation", "reduction de capital"]):
            capital_changes.append(entry)
        elif any(w in combined for w in ["dissolution", "liquidation", "radiation"]):
            dissolutions.append(entry)
        elif any(w in combined for w in ["transfert", "siege", "adresse"]):
            transferts.append(entry)
        elif any(w in combined for w in ["redressement", "procedure collective", "sauvegarde", "jugement"]):
            procedures.append(entry)
        else:
            autres.append(entry)

    # Signaux M&A detectes
    signaux_detectes = []
    if cessions:
        signaux_detectes.append({"signal": "bodacc_cession", "label": "Cession de fonds / parts", "count": len(cessions)})
    if capital_changes:
        signaux_detectes.append({"signal": "bodacc_capital_change", "label": "Modification de capital", "count": len(capital_changes)})
    if dissolutions:
        signaux_detectes.append({"signal": "bodacc_dissolution", "label": "Dissolution / Radiation", "count": len(dissolutions)})
    if transferts:
        signaux_detectes.append({"signal": "hq_relocation", "label": "Transfert de siege", "count": len(transferts)})
    if procedures:
        signaux_detectes.append({"signal": "procedure_collective", "label": "Procedure collective", "count": len(procedures)})

    return {
        "source": "pappers-mcp",
        "siren": siren,
        "nom_entreprise": data.get("nom_entreprise"),
        "statut_activite": "Radie" if data.get("entreprise_cessee") else "En activite",
        "procedure_collective_en_cours": data.get("procedure_collective_en_cours", False),
        "total_publications": len(publications),
        "signaux_ma": signaux_detectes,
        "cessions": cessions,
        "modifications_capital": capital_changes,
        "dissolutions": dissolutions,
        "transferts_siege": transferts,
        "procedures_bodacc": procedures,
        "autres": autres,
    }


@app.get("/api/pappers/dirigeant/search")
async def search_dirigeant_endpoint(
    q: str = Query(..., description="Nom et/ou prenom du dirigeant (ex: 'Dupont Jean')"),
    code_naf: Optional[str] = Query(None, description="Filtrer par code NAF"),
    departement: Optional[str] = Query(None, description="Filtrer par departement"),
):
    """
    Recherche toutes les entreprises ou une personne est ou a ete dirigeante.
    Utilise l'outil Pappers MCP reel : recherche-dirigeants (parametre q).
    Utile pour identifier les serial entrepreneurs et cartographier les reseaux.
    """
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Le parametre q doit contenir au moins 2 caracteres")

    data = await search_dirigeant_by_name(q.strip())
    if not data:
        raise HTTPException(status_code=404, detail=f"Aucun dirigeant trouve pour '{q}'")

    # Structure reelle Pappers recherche-dirigeants :
    # { "resultats": [ { "entreprises": [ { "siren":..., "nom_entreprise":...,
    #   "dirigeant": { "qualites":[...], "date_prise_de_poste":..., "actuel": bool } } ] } ],
    #   "total": N }
    # Chaque item de resultats = une personne, ses entreprises sont dans "entreprises"
    resultats = data.get("resultats") or []
    if not isinstance(resultats, list):
        resultats = []

    results = []
    for item in resultats[:50]:
        entreprises_raw = item.get("entreprises") or []

        # Construire la liste des mandats
        mandats = []
        for e in entreprises_raw[:15]:
            dir_info = e.get("dirigeant") or {}
            qualites = dir_info.get("qualites") or []
            mandats.append({
                "siren": e.get("siren"),
                "nom_entreprise": e.get("nom_entreprise") or e.get("denomination"),
                "code_naf": e.get("code_naf"),
                "libelle_naf": e.get("libelle_code_naf") or e.get("domaine_activite"),
                "ville": (e.get("siege") or {}).get("ville"),
                "qualite": ", ".join(qualites) if qualites else e.get("qualite"),
                "date_prise_de_poste": dir_info.get("date_prise_de_poste"),
                "en_fonction": dir_info.get("actuel", True),
                "statut_entreprise": "Radie" if e.get("entreprise_cessee") else "En activite",
            })

        # Infos personne : parfois dans le premier item, parfois absentes du MCP
        first = entreprises_raw[0] if entreprises_raw else {}
        dir0 = first.get("dirigeant") or {}

        results.append({
            "nb_mandats": len(entreprises_raw),
            "mandats_actifs": sum(1 for m in mandats if m["en_fonction"]),
            "mandats": mandats,
            "signal_multi_mandats": len(entreprises_raw) >= 2,
            # Info personne recuperee si disponible
            "date_premiere_prise_de_poste": dir0.get("date_premiere_prise_de_poste"),
        })

    return {
        "source": "pappers-mcp",
        "query": q,
        "total": data.get("total", len(results)),
        "nb_resultats": len(results),
        "data": results,
    }


@app.get("/api/pappers/procedures/{siren}")
async def get_procedures_endpoint(siren: str):
    """
    Procedures collectives d'une entreprise (redressement judiciaire, liquidation).
    Inclut aussi le score de risque Pappers et le statut d'activite.
    """
    siren = _validate_siren(siren)
    data = await get_pappers_procedures(siren)
    if not data or not isinstance(data, dict) or "raw" in data:
        raise HTTPException(status_code=404, detail=f"Entreprise SIREN {siren} non trouvee")

    procedures = data.get("procedures_collectives") or []
    if not isinstance(procedures, list):
        procedures = []

    cessee = data.get("entreprise_cessee", False)
    scoring_fi = data.get("scoring_financier")
    score_risque = None
    if isinstance(scoring_fi, dict):
        score_risque = scoring_fi.get("score")
    elif isinstance(scoring_fi, (int, float)):
        score_risque = scoring_fi

    niveau_risque = "Inconnu"
    if score_risque is not None:
        try:
            s = float(score_risque)
            if s >= 8:
                niveau_risque = "Tres eleve"
            elif s >= 6:
                niveau_risque = "Eleve"
            elif s >= 4:
                niveau_risque = "Modere"
            else:
                niveau_risque = "Faible"
        except (TypeError, ValueError):
            pass

    return {
        "source": "pappers-mcp",
        "siren": siren,
        "nom_entreprise": data.get("nom_entreprise"),
        "statut_activite": "Radie" if cessee else "En activite",
        "date_cessation": data.get("date_cessation"),
        "procedures_collectives": [
            {
                "type": p.get("type") or p.get("famille"),
                "date_jugement": p.get("date_jugement") or p.get("date"),
                "tribunal": p.get("tribunal"),
                "statut": p.get("statut") or p.get("etat"),
            }
            for p in procedures
        ],
        "en_procedure": len(procedures) > 0,
        "score_risque_pappers": score_risque,
        "niveau_risque": niveau_risque,
        "signal_ma": "procedure_collective" if procedures else None,
    }


@app.get("/api/pappers/concurrents/{siren}")
async def get_concurrents_endpoint(
    siren: str,
    ca_min: int = Query(0, description="CA minimum en euros (ex: 1000000 pour 1M)"),
    inclure_meme_departement: bool = Query(True, description="Restreindre au meme departement"),
):
    """
    Genere automatiquement une liste de concurrents pour une cible donnee.
    Recherche les entreprises actives avec le meme code NAF dans la meme region.
    Utile pour la consolidation sectorielle et l'identification de roll-up.
    """
    siren = _validate_siren(siren)

    # Recuperer les infos de la cible
    target_data = await get_pappers_company(siren)
    if not target_data or not isinstance(target_data, dict) or "raw" in target_data:
        raise HTTPException(status_code=404, detail=f"Entreprise SIREN {siren} non trouvee")

    code_naf = target_data.get("code_naf") or ""
    nom_entreprise = target_data.get("nom_entreprise") or ""
    siege = target_data.get("siege") or {}
    departement = siege.get("departement") or siege.get("code_postal", "")[:2] if siege.get("code_postal") else ""

    if not code_naf:
        raise HTTPException(status_code=400, detail="Code NAF introuvable pour cette entreprise")

    dep_query = departement if inclure_meme_departement else ""
    result = await get_pappers_concurrents(code_naf, dep_query, ca_min)

    if not result or not isinstance(result, dict):
        return {"data": [], "total": 0, "message": "Aucun concurrent trouve"}

    resultats = result.get("resultats") or []
    concurrents = []
    for r in resultats:
        if r.get("siren") == siren:
            continue  # Exclure la cible elle-meme
        siege_c = r.get("siege") or {}
        ca = r.get("chiffre_affaires")
        concurrents.append({
            "siren": r.get("siren"),
            "name": r.get("nom_entreprise"),
            "ville": siege_c.get("ville"),
            "departement": siege_c.get("departement"),
            "effectif": r.get("effectif"),
            "chiffre_affaires": ca,
            "chiffre_affaires_fmt": f"{ca/1e6:.1f}M EUR" if ca and ca > 0 else "N/A",
            "forme_juridique": r.get("forme_juridique"),
            "date_creation": r.get("date_creation"),
        })

    return {
        "source": "pappers-mcp",
        "cible": {
            "siren": siren,
            "nom": nom_entreprise,
            "code_naf": code_naf,
            "libelle_naf": target_data.get("libelle_code_naf"),
            "departement": departement,
        },
        "total_concurrents": result.get("total", len(concurrents)),
        "filtres": {
            "code_naf": code_naf,
            "departement": dep_query or "tous",
            "ca_min": ca_min,
        },
        "data": concurrents,
    }


@app.get("/api/pappers/score/{siren}")
async def get_score_defaillance_endpoint(siren: str, annee: Optional[str] = Query(None)):
    """
    Score de defaillance et indicateurs financiers Pappers pour une entreprise.
    Utilise scoring_non_financier (seul score dispo dans le MCP Pappers) +
    comptes-entreprise pour le detail des liasses comptables.
    """
    siren = _validate_siren(siren)

    # Appels paralleles : infos generales + comptes detailles (comptes peut timeout)
    results = await asyncio.gather(
        get_pappers_company(siren),
        get_comptes(siren, annee or ""),
        return_exceptions=True,
    )
    data = results[0] if not isinstance(results[0], Exception) else None
    comptes_data = results[1] if not isinstance(results[1], Exception) else None

    if not data or not isinstance(data, dict) or "raw" in data:
        raise HTTPException(status_code=404, detail=f"Entreprise SIREN {siren} non trouvee")

    scoring_nfi = data.get("scoring_non_financier") or {}
    finances = data.get("finances") or []

    # Score non-financier Pappers (seul disponible via MCP)
    score_nfi_val = None
    if isinstance(scoring_nfi, dict):
        score_nfi_val = scoring_nfi.get("score")
    elif isinstance(scoring_nfi, (int, float)):
        score_nfi_val = scoring_nfi

    # Niveau de risque EdRCF base sur score_non_financier
    niveau_risque = "Inconnu"
    if score_nfi_val is not None:
        try:
            s = float(score_nfi_val)
            if s >= 8:
                niveau_risque = "Tres eleve — distressed M&A possible"
            elif s >= 6:
                niveau_risque = "Eleve — surveillance renforcee"
            elif s >= 4:
                niveau_risque = "Modere — monitoring standard"
            else:
                niveau_risque = "Faible — cible saine"
        except (TypeError, ValueError):
            pass

    # Synthese financiere via finances (3 derniers exercices)
    synthese_finances = []
    for f in finances[:3]:
        annee_f = f.get("annee") or str(f.get("date_cloture_exercice", ""))[:4]
        ca = f.get("chiffre_affaires")
        synthese_finances.append({
            "annee": annee_f,
            "chiffre_affaires": ca,
            "chiffre_affaires_fmt": f"{ca/1e6:.1f}M EUR" if ca and ca > 0 else "N/A",
            "resultat": f.get("resultat"),
            "effectif": f.get("effectif"),
        })

    # Comptes detailles (liasses) depuis comptes-entreprise
    comptes_resume = {}
    if comptes_data and isinstance(comptes_data, dict):
        for annee_key, exercices in comptes_data.items():
            if isinstance(exercices, list) and exercices:
                ex = exercices[0]
                comptes_resume[annee_key] = {
                    "date_depot": ex.get("date_depot"),
                    "date_cloture": ex.get("date_cloture"),
                    "type_comptes": ex.get("libelle_type_comptes"),
                    "devise": ex.get("devise"),
                    "nb_sections": len(ex.get("sections") or []),
                }

    return {
        "source": "pappers-mcp",
        "siren": siren,
        "nom_entreprise": data.get("nom_entreprise"),
        "statut_activite": "Radie" if data.get("entreprise_cessee") else "En activite",
        "procedure_collective_en_cours": data.get("procedure_collective_en_cours", False),
        "scoring": {
            "score_non_financier": score_nfi_val,
            "detail_non_financier": scoring_nfi if isinstance(scoring_nfi, dict) else {},
            "niveau_risque_edrcf": niveau_risque,
            "note": "Seul le scoring non-financier est disponible via MCP Pappers",
        },
        "synthese_financiere": synthese_finances,
        "comptes_annuels": comptes_resume,
        "procedures_collectives": data.get("procedures_collectives") or [],
    }


@app.get("/api/targets/{target_id}")
async def get_target(target_id: str):
    # 1) Lookup by id
    target = next((t for t in enriched_targets if t["id"] == target_id), None)
    if target:
        return {"data": target}
    # 2) Maybe target_id is a SIREN — try to fetch from Pappers and add
    if target_id.replace("-", "").isdigit():
        siren = target_id.replace("edrcf-", "").replace("edrcf", "")
        if len(siren) == 9:
            added = await _add_company_to_targets(siren)
            if added:
                return {"data": added}
    raise HTTPException(status_code=404, detail="Target not found")


@app.get("/api/news/{siren}")
async def get_news_for_company(siren: str):
    """
    Fetch recent press articles from Google News RSS for a company.
    Returns articles with M&A signal detection.
    Optimised: Pappers name lookup + Google News run concurrently with 8s guard.
    """
    siren = siren.strip().replace(" ", "")
    # Fast path: target already in memory
    target = next((t for t in enriched_targets if t.get("siren") == siren), None)
    if target:
        company_name = target["name"]
        articles = await asyncio.wait_for(get_google_news(company_name), timeout=8)
    else:
        # Slow path: need Pappers lookup — run concurrently with a generous timeout
        async def _resolve_and_fetch():
            try:
                pappers_data = await asyncio.wait_for(get_pappers_company(siren), timeout=6)
                name = (pappers_data or {}).get("nom_entreprise") or siren
            except Exception:
                name = siren
            return name, await get_google_news(name)

        try:
            company_name, articles = await asyncio.wait_for(_resolve_and_fetch(), timeout=9)
        except asyncio.TimeoutError:
            company_name, articles = siren, []

    # Aggregate detected signals across all articles
    detected_signals: set = set()
    for a in articles:
        for sig in a.get("signals", []):
            detected_signals.add(sig)

    return {
        "data": {
            "company": company_name,
            "siren": siren,
            "articles": articles,
            "signals_detected": list(detected_signals),
        }
    }


@app.get("/api/infogreffe/{siren}")
async def get_infogreffe_endpoint(siren: str):
    """
    Fetch recent actes RCS from Infogreffe open data for a SIREN.
    """
    siren = _validate_siren(siren)
    try:
        actes = await asyncio.wait_for(get_infogreffe_actes(siren), timeout=8)
    except asyncio.TimeoutError:
        actes = []
    # Detect signals from actes
    detected_signals: set = set()
    for acte in actes:
        acte_type = (acte.get("type") or "").lower()
        if any(w in acte_type for w in ["nomination", "gerant", "president", "directeur"]):
            detected_signals.add("infogreffe_nouveau_dirigeant")
        if any(w in acte_type for w in ["capital", "augmentation", "reduction"]):
            detected_signals.add("infogreffe_capital_change")
        if any(w in acte_type for w in ["fusion", "absorption", "scission"]):
            detected_signals.add("infogreffe_fusion_absorption")
        if any(w in acte_type for w in ["transfert", "siege"]):
            detected_signals.add("infogreffe_transfert_siege")

    return {
        "data": {
            "siren": siren,
            "actes": actes,
            "signals_detected": list(detected_signals),
        }
    }


@app.get("/api/signals")
def get_signals(severity: Optional[str] = Query(None)):
    signals_feed = []
    for t in enriched_targets:
        for sig in t["topSignals"]:
            if severity and sig["severity"] != severity:
                continue
            signals_feed.append(
                {
                    "id": f"{t['id']}-{sig['id']}",
                    "type": sig["family"],
                    "title": f"{sig['label']} — {t['name']}",
                    "time": "Recent",
                    "source": sig["source"],
                    "source_url": sig["source_url"],
                    "severity": sig["severity"],
                    "location": f"{t['city']}, {t['region']}",
                    "tags": [sig["family"], t["sector"]],
                    "target_id": t["id"],
                    "target_name": t["name"],
                    "dimension": sig["dimension"],
                    "points": sig["points"],
                }
            )
    # Sort: high first, then medium, then low
    order = {"high": 0, "medium": 1, "low": 2}
    signals_feed.sort(key=lambda s: order.get(s["severity"], 3))
    return {"data": signals_feed, "total": len(signals_feed), "catalog": SIGNAL_CATALOG}


@app.get("/api/pipeline")
def get_pipeline():
    """5 M&A stages pipeline"""
    pipeline = [
        {"id": "origination", "title": "Origination", "color": "indigo", "cards": []},
        {"id": "qualification", "title": "Qualification", "color": "purple", "cards": []},
        {"id": "pitch", "title": "Pitch", "color": "amber", "cards": []},
        {"id": "execution", "title": "Execution", "color": "emerald", "cards": []},
        {"id": "closing", "title": "Closing", "color": "green", "cards": []},
    ]
    for t in enriched_targets:
        card = {
            "id": t["id"],
            "name": t["name"],
            "sector": t["sector"],
            "score": t["globalScore"],
            "priority": t["priorityLevel"],
            "tags": [t["analysis"]["type"]],
            "window": t["analysis"]["window"],
            "ebitda": t["financials"]["ebitda"],
        }
        if t["globalScore"] >= 65:
            pipeline[1]["cards"].append(card)  # Qualification (already scored high)
        elif t["globalScore"] >= 45:
            pipeline[0]["cards"].append(card)  # Origination

    return {"data": pipeline}


@app.post("/api/pipeline/move")
def move_pipeline_card(
    card_id: str = Query(...),
    from_stage: str = Query(...),
    to_stage: str = Query(...),
):
    return {
        "success": True,
        "message": f"Carte {card_id} deplacee de {from_stage} vers {to_stage}",
    }


@app.get("/api/scoring/config")
def get_scoring_config():
    return {"data": scoring_config}


@app.post("/api/scoring/config")
def update_scoring_config(config: Dict[str, Any]):
    global enriched_targets
    for key, val in config.items():
        if key in scoring_config:
            scoring_config[key].update(val)
    enriched_targets = [enrich_target(c) for c in raw_targets]
    return {
        "data": scoring_config,
        "message": "Ponderations mises a jour. Scores recalcules.",
    }


def build_target_from_search(idx, search_result, search_context=None):
    """Build an EdRCF target from Pappers search result, using search context for signal detection."""
    from pappers_loader import map_sector, map_region, map_structure, build_risks

    ctx = search_context or {}
    siege = search_result.get("siege", {}) or {}
    ca = search_result.get("chiffre_affaires", 0) or 0
    siren = search_result.get("siren", "")
    name = search_result.get("nom_entreprise", "")
    libelle_naf = search_result.get("libelle_code_naf", "")
    code_naf = search_result.get("code_naf", "")
    ville = siege.get("ville", "")
    cp = siege.get("code_postal", "")
    effectif = search_result.get("effectif", "N/A")
    date_creation = search_result.get("date_creation", "")
    forme_juridique = search_result.get("forme_juridique", "")

    sector = map_sector(code_naf, libelle_naf)
    region = map_region(cp)
    structure = map_structure(forme_juridique)

    # Format financials
    ca_fmt = f"{ca / 1e6:.1f}M EUR" if ca > 0 else "N/A"
    ebitda_est = ca * 0.15
    ebitda_fmt = f"{ebitda_est / 1e6:.1f}M EUR" if ca > 0 else "N/A"
    ebitda_margin = "15.0%" if ca > 0 else "N/A"

    from pappers_loader import compute_ebitda_range
    ebitda_range = compute_ebitda_range(ebitda_est)

    # Smart signal detection using search context
    signals = []
    age_min = int(ctx.get("age_dirigeant_min", 0) or 0)
    if age_min >= 60:
        signals.append("founder_60_no_successor")
        if age_min >= 65:
            signals.append("director_withdrawal")
    if age_min >= 55:
        signals.append("director_speaker")
    # Sector signals
    sector_data = SECTORS_HEAT.get(sector)
    if sector_data and sector_data.get("heat", 0) >= 60:
        signals.append("sector_consolidation")
    # Financial signals
    if ca > 10e6:
        signals.append("ca_growth_2years")
        signals.append("headcount_growth_20")
    elif ca > 3e6:
        signals.append("ca_growth_2years")
    # Holding / structure signals
    if "holding" in (libelle_naf or "").lower():
        signals.append("holding_creation")
    if ca > 5e6:
        signals.append("big4_audit")
    # Always add establishment if multi-site
    if effectif and any(s in str(effectif) for s in ("50", "100", "200")):
        signals.append("new_establishment")
    signals.append("press_regional")
    # Deduplicate and validate
    signals = list(dict.fromkeys(s for s in signals if s in SIGNAL_CATALOG)) or ["press_regional"]

    from pappers_loader import build_analysis as _build_analysis

    est_age = max(age_min, 62) if age_min >= 55 else 0
    dirigeants = [{"name": "Dirigeant principal", "role": "President", "age": est_age, "since": "N/A"}]
    analysis = _build_analysis(signals, sector, {}, dirigeants)
    risks = build_risks(signals)

    return {
        "id": f"edrcf-{idx:03d}",
        "siren": siren,
        "name": name,
        "sector": sector,
        "sub_sector": libelle_naf or "N/A",
        "region": region,
        "city": ville or "France",
        "code_naf": code_naf or "",
        "creation_date": date_creation,
        "structure": structure,
        "publication_status": "Publie",
        "dirigeants": dirigeants,
        "financials": {
            "revenue": ca_fmt,
            "revenue_growth": "N/A",
            "ebitda": ebitda_fmt,
            "ebitda_margin": ebitda_margin,
            "ebitda_range": ebitda_range,
            "effectif": effectif or "N/A",
            "last_published_year": 2024,
        },
        "active_signals": signals,
        "group": {"is_group": False, "parent": None, "subsidiaries": [], "consolidated_revenue": None},
        "relationship": {
            "strength": max(5, min(50, len(signals) * 8)),
            "path": "Identifie via Copilot Pappers",
            "common_connections": 0,
            "edr_banker": None,
        },
        "analysis": analysis,
        "activation": {
            "deciders": ["A identifier"],
            "approach": "Qualification via screening Pappers",
            "reason": f"Entreprise identifiee par le Copilot IA dans le secteur {sector}.",
        },
        "risks": risks,
    }


from fastapi.responses import StreamingResponse


@app.get("/api/copilot/stream")
async def copilot_stream_endpoint(q: str = Query(...)):
    """Server-Sent Events streaming version of the copilot.
    Yields: data: {"chunk": "..."}\n\n  and  data: {"done": true, "source": "...", "targets_updated": bool}\n\n
    """
    async def generate():
        global enriched_targets, raw_targets
        targets_updated = False

        context_lines = [
            f"- {t['name']} ({t['sector']}, {t.get('city','?')}): Score {t['globalScore']}, {t['priorityLevel']}"
            for t in enriched_targets[:5]
        ]
        context = f"Cibles EdRCF ({len(enriched_targets)} total):\n" + "\n".join(context_lines)

        # SIREN direct lookup
        siren_match = re.search(r'\b(\d{9})\b', q)
        if siren_match:
            siren_val = siren_match.group(1)
            try:
                company_info = await _papperclip_get_company(siren_val)
                if company_info and isinstance(company_info, dict) and company_info.get("siren"):
                    await _add_company_to_targets(siren_val)
                    targets_updated = True
                    nom = company_info.get("nom_entreprise", siren_val)
                    siege = company_info.get("siege") or {}
                    ville = siege.get("ville", "")
                    naf = company_info.get("libelle_code_naf", "")
                    ca = company_info.get("chiffre_affaires", 0)
                    ca_str = f"{ca/1e6:.1f}M EUR" if ca and ca > 0 else "N/A"
                    reps = company_info.get("representants") or []
                    rep_lines = "\n".join([
                        f"  - {r.get('prenom','')} {r.get('nom','')} ({r.get('qualite','')})"
                        for r in reps[:3]
                    ])
                    text = (
                        f"**{nom}** — SIREN {siren_val}\n\n"
                        f"- **Siège** : {ville}\n"
                        f"- **Activité** : {naf}\n"
                        f"- **CA** : {ca_str}\n\n"
                        f"**Dirigeants :**\n{rep_lines or '  N/A'}\n\n"
                        f"*Entreprise ajoutée à la base EdRCF.*"
                    )
                    # Simulate streaming for rule-based response
                    chunk_size = 40
                    for i in range(0, len(text), chunk_size):
                        yield f"data: {json.dumps({'chunk': text[i:i+chunk_size]})}\n\n"
                    yield f"data: {json.dumps({'done': True, 'source': 'pappers', 'targets_updated': True})}\n\n"
                    return
            except Exception as e:
                print(f"[Stream] SIREN lookup error: {e}")

        # Stream AI response
        ai_streamed = False
        async for chunk in copilot_ai_query_stream(q, context):
            ai_streamed = True
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

        if not ai_streamed:
            # Fallback: call existing rule-based copilot
            try:
                result = await copilot_query(q=q)
                text = result.get("response", "Désolé, je n'ai pas pu traiter cette demande.")
                targets_updated = result.get("targets_updated", False)
                chunk_size = 40
                for i in range(0, len(text), chunk_size):
                    yield f"data: {json.dumps({'chunk': text[i:i+chunk_size]})}\n\n"
                done_event: dict = {'done': True, 'source': result.get('source', 'rule-based'), 'targets_updated': targets_updated}
                if targets_updated:
                    done_event['targets_count'] = len(enriched_targets)
                yield f"data: {json.dumps(done_event)}\n\n"
                return
            except Exception as e:
                yield f"data: {json.dumps({'chunk': 'Erreur de connexion. Veuillez réessayer.'})}\n\n"

        done_event = {'done': True, 'source': 'ai', 'targets_updated': targets_updated}
        if targets_updated:
            done_event['targets_count'] = len(enriched_targets)
        yield f"data: {json.dumps(done_event)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/copilot/query")
async def copilot_query(q: str = Query(...)):
    global enriched_targets, raw_targets

    # Build compact context from local targets (top 5 only to save tokens)
    context_lines = []
    for t in enriched_targets[:5]:
        context_lines.append(
            f"- {t['name']} ({t['sector']}, {t['city']}): Score {t['globalScore']}, "
            f"{t['priorityLevel']}, {t['analysis']['type']}, {t['analysis']['window']}"
        )
    context = f"Cibles EdRCF ({len(enriched_targets)} total, top 5):\n" + "\n".join(context_lines)

    # --- Detect if user wants Pappers data and enrich context ---
    ql = q.lower()
    pappers_context = ""
    pappers_filters = {}
    targets_updated = False

    # --- SIREN lookup FIRST (before anything else) ---
    siren_match = re.search(r'\b(\d{9})\b', q)
    if siren_match:
        siren_val = siren_match.group(1)
        try:
            data = await get_pappers_company(siren_val)
            if data and isinstance(data, dict) and "raw" not in data and data.get("nom_entreprise"):
                nom = data.get("nom_entreprise", "Entreprise inconnue")
                siege = data.get("siege") or {}
                ville = siege.get("ville", "")
                dept = siege.get("departement", "")
                naf = data.get("libelle_code_naf", "")
                ca = data.get("chiffre_affaires")
                ca_str = f"{ca/1e6:.1f}M EUR" if ca and ca > 0 else "N/A"
                effectif = data.get("effectif", "N/A")
                cessee = data.get("entreprise_cessee", False)
                statut = "Radiee" if cessee else "Active"
                date_cess = data.get("date_cessation", "")
                reps = data.get("representants") or []
                rep_lines = "\n".join([
                    f"  - {(r.get('prenom') or '')} {(r.get('nom') or '')} — {r.get('qualite', '')}"
                    for r in reps[:3]
                ])
                date_crea = data.get("date_creation", "")
                forme = data.get("forme_juridique", "")
                capital = data.get("capital")
                capital_str = f"{capital/1000:.0f}k EUR" if capital else "N/A"
                # Add to targets
                await _add_company_to_targets(siren_val)
                resp_lines = [
                    f"**{nom}** — SIREN {siren_val}\n",
                    f"- **Statut** : {statut}" + (f" ({date_cess})" if date_cess else ""),
                    f"- **Siège** : {ville}{', ' + dept if dept else ''}",
                    f"- **Activité** : {naf}",
                    f"- **Forme juridique** : {forme}",
                    f"- **Création** : {date_crea}",
                    f"- **CA** : {ca_str}  |  **Effectif** : {effectif}  |  **Capital** : {capital_str}",
                    "",
                    "**Dirigeants :**",
                    rep_lines if rep_lines else "  N/A",
                    "",
                    "*Source : Pappers MCP — données open data*",
                ]
                return {
                    "response": "\n".join(resp_lines),
                    "source": "pappers-mcp",
                    "targets_updated": True,
                }
            else:
                return {
                    "response": f"Aucune entreprise trouvée pour le SIREN **{siren_val}** dans la base Pappers.",
                    "source": "pappers-mcp",
                    "targets_updated": False,
                }
        except Exception as e:
            print(f"[Copilot] SIREN lookup error: {e}")

    # Broad intent detection — trigger Pappers for sector/screening queries
    wants_pappers = any(w in ql for w in [
        "pappers", "screening", "screener", "scan", "prospecter", "nouvelles cibles",
        "open data", "pme", "eti",
        "ca superieur", "chiffre affaires",
        "salarie", "salarié", "effectif",
    ])

    # Sector → NAF code mapping (broad)
    sector_naf_map = {
        "courtage": "66.22Z", "assurance": "66.22Z",
        "industri": "25,28,29", "mecanique": "25.62A", "usinage": "25.62A",
        "logistique": "49.41A,52", "transport": "49.41A,49.41B",
        "medtech": "32.50A", "medical": "32.50A", "sante": "32.50A,86",
        "pharma": "21", "clinique": "86.10Z",
        "conseil": "70.22Z", "consulting": "70.22Z",
        "btp": "41.20A,41.20B", "construction": "41.20A,41.20B", "batiment": "41.20A",
        "agroalimentaire": "10", "alimentaire": "10", "restaur": "56",
        "bar": "56.30Z", "hotel": "55.10Z", "hotellerie": "55.10Z",
        "energie": "35.11Z,43.21A", "solaire": "43.21A", "photovoltaique": "43.21A",
        "logiciel": "62.01Z", "saas": "62.01Z", "informatique": "62.01Z",
        "ia": "62.01Z", "intelligence artificielle": "62.01Z",
        "tech": "62.01Z", "numerique": "62.01Z", "digital": "62.01Z",
        "holding": "64.20Z", "immobilier": "68", "finance": "64",
        "luxe": "14.13Z", "mode": "14.13Z", "textile": "13",
        "automobile": "29.10Z", "aeronautique": "30.30Z",
        "environnement": "37,38,39", "recyclage": "38",
        "securite": "80.10Z", "nettoyage": "81.21Z",
        "education": "85", "formation": "85.59A",
        "telecom": "61", "communication": "73",
    }

    detected_naf = None
    for keyword, naf in sector_naf_map.items():
        if keyword in ql:
            detected_naf = naf
            wants_pappers = True
            break

    # Detect age filters
    if any(w in ql for w in ["60 ans", "65 ans", "senior", "succession", "retraite"]):
        pappers_filters["age_dirigeant_min"] = "60"
        wants_pappers = True
    if any(w in ql for w in ["fondateur", "dirigeant age"]):
        pappers_filters["age_dirigeant_min"] = "58"
        wants_pappers = True

    # Detect financial filters from natural language
    ca_match = re.search(r"(\d+)\s*(?:m€|m\b|millions?|meur)", ql)
    if ca_match:
        ca_val = int(ca_match.group(1)) * 1_000_000
        pappers_filters["chiffre_affaires_min"] = str(ca_val)
        wants_pappers = True

    eff_match = re.search(r"(\d+)\s*(?:salari|employ|effectif)", ql)
    if eff_match:
        pappers_filters["nombre_salaries_min"] = eff_match.group(1)
        wants_pappers = True

    if detected_naf:
        pappers_filters["code_naf"] = detected_naf

    # Default CA filter if none set
    if wants_pappers and "chiffre_affaires_min" not in pappers_filters:
        pappers_filters["chiffre_affaires_min"] = "3000000"

    pappers_filters["par_page"] = "50"

    if wants_pappers:
        try:
            pappers_data = await search_pappers(**pappers_filters)
            if isinstance(pappers_data, dict) and "resultats" in pappers_data:
                resultats = pappers_data["resultats"][:50]
                total = pappers_data.get("total", 0)
                pappers_lines = [f"\nPappers ({total} resultats, {len(resultats)} affiches):"]
                for r in resultats:
                    nom = r.get("nom_entreprise", "?")
                    siren = r.get("siren", "?")
                    ville = (r.get("siege") or {}).get("ville", "?")
                    ca = r.get("chiffre_affaires")
                    ca_str = f"{ca/1e6:.1f}M" if ca and ca > 0 else "N/A"
                    eff = r.get("effectif", "?")
                    cap = r.get("capital", "?")
                    pappers_lines.append(
                        f"- {nom} ({siren}, {ville}) CA:{ca_str}, Eff:{eff}, Cap:{cap}"
                    )
                pappers_context = "\n".join(pappers_lines)

                # --- MERGE new results into existing targets (don't replace) ---
                async with _targets_lock:
                    existing_sirens = {t.get("siren") for t in enriched_targets}
                    added_count = 0
                    for idx, r in enumerate(resultats):
                        siren = r.get("siren", "")
                        if not siren or siren in existing_sirens:
                            continue
                        existing_sirens.add(siren)
                        new_target = build_target_from_search(len(enriched_targets) + added_count + 1, r, pappers_filters)
                        raw_targets.append(new_target)
                        enriched_targets.append(enrich_target(new_target))
                        added_count += 1

                    if added_count:
                        enriched_targets.sort(key=lambda x: x["globalScore"], reverse=True)
                        save_cache(raw_targets)
                        targets_updated = True
                    print(f"[Copilot] Added {added_count} targets from Pappers (total: {len(enriched_targets)})")

        except Exception as e:
            print(f"[Copilot] Pappers enrichment error: {e}")

    # --- Direct company name search (short query, no trigger keywords, likely a company name) ---
    is_company_name_search = (
        not wants_pappers
        and not siren_match
        and len(ql.strip()) >= 2
        and len(ql.split()) <= 5
    )
    if is_company_name_search:
        try:
            pappers_result = await search_pappers(q)
            if isinstance(pappers_result, dict) and pappers_result.get("resultats"):
                resultats = pappers_result["resultats"][:5]
                total = pappers_result.get("total", len(resultats))
                lines = [f"**Recherche Pappers pour \"{q}\" — {total} résultat(s) :**\n"]
                add_tasks = []
                for r in resultats:
                    nom = r.get("nom_entreprise", "N/A")
                    siren_r = r.get("siren", "")
                    siege_r = r.get("siege") or {}
                    ville_r = siege_r.get("ville", "")
                    naf_r = r.get("libelle_code_naf", "")
                    ca_r = r.get("chiffre_affaires")
                    ca_str_r = f"{ca_r/1e6:.1f}M" if ca_r and ca_r > 0 else "N/A"
                    eff_r = r.get("effectif", "")
                    reps_r = r.get("representants") or []
                    lines.append(f"**{nom}** (SIREN : {siren_r})")
                    if ville_r:
                        lines.append(f"  Siège : {ville_r}")
                    if naf_r:
                        lines.append(f"  Activité : {naf_r}")
                    if ca_str_r != "N/A":
                        lines.append(f"  CA : {ca_str_r}  |  Effectif : {eff_r or 'N/A'}")
                    for rep in reps_r[:1]:
                        lines.append(f"  Dirigeant : {(rep.get('prenom') or '')} {(rep.get('nom') or '')} — {rep.get('qualite', '')}")
                    lines.append("")
                    if siren_r:
                        add_tasks.append(_add_company_to_targets(siren_r))
                lines.append("*Source : Pappers MCP — données open data*")
                # Add found companies to targets in background
                if add_tasks:
                    await asyncio.gather(*add_tasks, return_exceptions=True)
                return {
                    "response": "\n".join(lines),
                    "source": "pappers-mcp",
                    "targets_updated": bool(add_tasks),
                }
        except Exception as e:
            print(f"[Copilot] Company name search error: {e}")

    full_context = context + pappers_context

    # Try DeepSeek AI with enriched context
    ai_response = await copilot_ai_query(q, full_context)
    if ai_response:
        source = "deepseek-ai+pappers" if pappers_context else "deepseek-ai"
        return {"response": ai_response, "source": source, "targets_updated": targets_updated}

    # Fallback: rule-based copilot
    await asyncio.sleep(0.3)
    ql = q.lower()

    # --- Smart matching on specific targets ---
    for t in enriched_targets:
        name_words = t["name"].lower().split()
        # Match on any significant word of the company name (skip short words)
        matched = any(
            word in ql
            for word in name_words
            if len(word) > 3 and word not in ("group", "groupe", "les", "des", "the")
        )
        if matched or t["name"].lower() in ql:
            signal_lines = "\n".join(
                [
                    f"  - {s['label']} ({s['source']}, +{s['points']}pts)"
                    for s in t["topSignals"][:6]
                ]
            )
            dirigeant_lines = "\n".join(
                [
                    f"  - {d['name']} — {d['role']}, {d['age']} ans (depuis {d['since']})"
                    for d in t["dirigeants"]
                ]
            )
            return {
                "response": (
                    f"**{t['name']}** ({t['sector']}, {t['city']})\n\n"
                    f"Score Global : **{t['globalScore']}/100** — **{t['priorityLevel']}**\n\n"
                    f"**These strategique :** {t['analysis']['type']} "
                    f"(fenetre {t['analysis']['window']})\n\n"
                    f"{t['analysis']['narrative']}\n\n"
                    f"**Dirigeants :**\n{dirigeant_lines}\n\n"
                    f"**Financiers :** CA {t['financials']['revenue']} "
                    f"({t['financials']['revenue_growth']}), "
                    f"EBITDA {t['financials']['ebitda']} "
                    f"(marge {t['financials']['ebitda_margin']}), "
                    f"{t['financials']['effectif']} salaries\n\n"
                    f"**Signaux actifs ({len(t['topSignals'])}) :**\n{signal_lines}\n\n"
                    f"**Activation :** {t['activation']['approach']}\n\n"
                    f"**Risque faux positif :** {t['risks']['falsePositive']}"
                ),
                "source": "rule-based",
                "targets_updated": targets_updated,
            }

    # --- Top / Best / Priority queries ---
    if any(w in ql for w in ["meilleur", "top", "priorit", "action", "best", "classement", "ranking"]):
        top = sorted(enriched_targets, key=lambda x: x["globalScore"], reverse=True)[:5]
        lines = ["**Top 5 cibles par score EDRCF :**\n"]
        for i, t in enumerate(top, 1):
            lines.append(
                f"{i}. **{t['name']}** — Score **{t['globalScore']}** ({t['priorityLevel']})\n"
                f"   {t['sector']} | {t['city']} | {t['analysis']['type']} | "
                f"Fenetre {t['analysis']['window']}"
            )
        return {"response": "\n".join(lines), "source": "rule-based", "targets_updated": targets_updated}

    # --- Sector / Industry analysis ---
    if any(w in ql for w in ["secteur", "sector", "industri", "consolid", "chaleur", "heat"]):
        # Check if asking about a specific sector
        specific_sector = None
        for sector_name in SECTORS_HEAT:
            if any(word in ql for word in sector_name.lower().split("/") if len(word.strip()) > 3):
                specific_sector = sector_name
                break
            if any(word.strip().lower() in ql for word in sector_name.lower().replace("/", " ").split() if len(word.strip()) > 3):
                specific_sector = sector_name
                break

        if specific_sector:
            data = SECTORS_HEAT[specific_sector]
            sector_targets = [t for t in enriched_targets if t["sector"] == specific_sector]
            lines = [
                f"**Analyse sectorielle : {specific_sector}**\n",
                f"Indice de chaleur : **{data['heat']}%** ({data['indicator']})\n",
                f"{data['detail']}\n",
                f"**{len(sector_targets)} cible(s) suivie(s) :**\n",
            ]
            for t in sorted(sector_targets, key=lambda x: x["globalScore"], reverse=True):
                lines.append(
                    f"  - **{t['name']}** (Score {t['globalScore']}) — "
                    f"{t['analysis']['type']}, fenetre {t['analysis']['window']}"
                )
            return {"response": "\n".join(lines), "source": "rule-based", "targets_updated": targets_updated}

        lines = ["**Analyse sectorielle EDRCF :**\n"]
        for sector, data in sorted(SECTORS_HEAT.items(), key=lambda x: x[1]["heat"], reverse=True):
            count = len([t for t in enriched_targets if t["sector"] == sector])
            lines.append(
                f"- **{sector}** — Chaleur **{data['heat']}%** ({data['indicator']})\n"
                f"  {data['detail']}\n"
                f"  {count} cible(s) suivie(s)"
            )
        return {"response": "\n".join(lines), "source": "rule-based", "targets_updated": targets_updated}

    # --- Founder / Succession / Age queries ---
    if any(w in ql for w in ["fondateur", "succession", "dirigeant", "age", "60", "65", "70", "senior", "retraite"]):
        founders = [
            t
            for t in enriched_targets
            if any(d.get("age", 0) >= 60 for d in t["dirigeants"])
        ]
        lines = [f"**{len(founders)} societes avec fondateur/dirigeant de 60 ans ou plus :**\n"]
        for t in sorted(
            founders,
            key=lambda x: max(d.get("age", 0) for d in x["dirigeants"]),
            reverse=True,
        ):
            d = max(t["dirigeants"], key=lambda x: x.get("age", 0))
            lines.append(
                f"- **{t['name']}** — {d['name']} ({d['age']} ans, {d['role']})\n"
                f"  Score {t['globalScore']} | {t['analysis']['type']} | "
                f"Fenetre {t['analysis']['window']}"
            )
        return {"response": "\n".join(lines), "source": "rule-based", "targets_updated": targets_updated}

    # --- Filter / Search help ---
    if any(w in ql for w in ["filtre", "filter", "region", "taille", "cherch", "recherch", "comment"]):
        regions = sorted(set(t["region"] for t in enriched_targets))
        return {
            "response": (
                "**Filtres disponibles dans l'Intelligence Vault :**\n\n"
                f"- **Secteur** : {len(SECTORS_HEAT)} secteurs couverts "
                f"({', '.join(list(SECTORS_HEAT.keys())[:4])}...)\n"
                f"- **Region** : {', '.join(regions)}\n"
                "- **Taille EBITDA** : < 3M EUR / 3-10M EUR / 10-30M EUR / > 30M EUR\n"
                "- **Score minimum** : Curseur 0-100\n"
                "- **Structure** : Familiale / PE-backed / Groupe cote\n"
                "- **Publication** : Publie / Ne publie pas\n\n"
                "Utilisez les filtres dans la page Intelligence Vault ou posez-moi "
                "une question specifique (ex: \"cibles familiales en Bretagne\")."
            ),
            "source": "rule-based",
            "targets_updated": targets_updated,
        }

    # --- Pipeline / Deal / Mandate status ---
    if any(w in ql for w in ["pipeline", "deal", "mandat", "funnel", "flux", "statut"]):
        stages = {
            "Action Prioritaire": 0,
            "Qualification": 0,
            "Monitoring": 0,
            "Veille Passive": 0,
        }
        for t in enriched_targets:
            stages[t["priorityLevel"]] = stages.get(t["priorityLevel"], 0) + 1
        total_score = sum(t["globalScore"] for t in enriched_targets)
        avg_score = round(total_score / len(enriched_targets), 1)
        return {
            "response": (
                f"**Etat du Pipeline EDRCF :**\n\n"
                f"Action Prioritaire : **{stages.get('Action Prioritaire', 0)}** cibles\n"
                f"Qualification : **{stages.get('Qualification', 0)}** cibles\n"
                f"Monitoring : **{stages.get('Monitoring', 0)}** cibles\n"
                f"Veille Passive : **{stages.get('Veille Passive', 0)}** cibles\n\n"
                f"**Total : {len(enriched_targets)} entites surveillees** "
                f"(score moyen : {avg_score})\n\n"
                f"1 mandat en execution (TechParts International), "
                f"1 en closing (LogiNord Express, Q2 2026).\n\n"
                f"**Prochaines actions recommandees :**\n"
                f"- Approcher Groupe Mercier Industrie via Pierre Legrand (banquier prive)\n"
                f"- Rencontrer Philippe Renaud (Courtage Prestige) au prochain evenement CSCA\n"
                f"- Coverage InfraVia Capital pour DataPulse Technologies"
            ),
            "source": "rule-based",
            "targets_updated": targets_updated,
        }

    # --- Signal-related queries ---
    if any(w in ql for w in ["signal", "alerte", "radar", "detection", "nouveau"]):
        high_signals = []
        for t in enriched_targets:
            for s in t["topSignals"]:
                if s["severity"] == "high":
                    high_signals.append((t, s))
        lines = [f"**{len(high_signals)} signaux de severite haute detectes :**\n"]
        for t, s in high_signals[:10]:
            lines.append(
                f"- **{s['label']}** — {t['name']} ({t['city']})\n"
                f"  Source: {s['source']} | +{s['points']}pts | "
                f"Dimension: {s['dimension']}"
            )
        lines.append(
            f"\n**Total signaux actifs : "
            f"{sum(len(t['topSignals']) for t in enriched_targets)}** "
            f"sur {len(enriched_targets)} cibles"
        )
        return {"response": "\n".join(lines), "source": "rule-based", "targets_updated": targets_updated}

    # --- LBO / PE-backed queries ---
    if any(w in ql for w in ["lbo", "pe-backed", "private equity", "fonds", "sponsor"]):
        pe_targets = [t for t in enriched_targets if t["structure"] == "PE-backed"]
        lines = [f"**{len(pe_targets)} cibles PE-backed suivies :**\n"]
        for t in sorted(pe_targets, key=lambda x: x["globalScore"], reverse=True):
            parent = t["group"].get("parent", "N/A")
            lines.append(
                f"- **{t['name']}** (Score {t['globalScore']})\n"
                f"  Actionnaire : {parent}\n"
                f"  {t['analysis']['type']} | Fenetre {t['analysis']['window']}"
            )
        return {"response": "\n".join(lines), "source": "rule-based", "targets_updated": targets_updated}

    # --- Familiale / Family queries ---
    if any(w in ql for w in ["familial", "famille", "family", "transmission"]):
        fam_targets = [t for t in enriched_targets if t["structure"] == "Familiale"]
        lines = [f"**{len(fam_targets)} cibles familiales suivies :**\n"]
        for t in sorted(fam_targets, key=lambda x: x["globalScore"], reverse=True):
            d = t["dirigeants"][0]
            lines.append(
                f"- **{t['name']}** (Score {t['globalScore']}) — {d['name']}, {d['age']} ans\n"
                f"  {t['sector']} | {t['city']} | {t['analysis']['type']}"
            )
        return {"response": "\n".join(lines), "source": "rule-based", "targets_updated": targets_updated}

    # --- Region-specific queries ---
    for t in enriched_targets:
        region_words = t["region"].lower().replace("-", " ").split()
        city_lower = t["city"].lower()
        if city_lower in ql or any(w in ql for w in region_words if len(w) > 3):
            matching = [
                x
                for x in enriched_targets
                if x["region"] == t["region"] or x["city"].lower() in ql
            ]
            if len(matching) > 1 or t["city"].lower() not in ql:
                lines = [
                    f"**Cibles en {t['region']} :**\n"
                ]
                for m in sorted(matching, key=lambda x: x["globalScore"], reverse=True):
                    lines.append(
                        f"- **{m['name']}** ({m['city']}) — Score {m['globalScore']}\n"
                        f"  {m['sector']} | {m['analysis']['type']}"
                    )
                return {"response": "\n".join(lines), "source": "rule-based", "targets_updated": targets_updated}

    # --- EBITDA / Financial queries ---
    if any(w in ql for w in ["ebitda", "chiffre", "revenue", "financ", "marge", "rentab"]):
        sorted_by_ebitda = sorted(
            enriched_targets,
            key=lambda x: float(
                x["financials"]["ebitda"].replace("M EUR", "").replace(",", ".")
            ),
            reverse=True,
        )
        lines = ["**Classement par EBITDA :**\n"]
        for t in sorted_by_ebitda[:8]:
            lines.append(
                f"- **{t['name']}** — EBITDA {t['financials']['ebitda']} "
                f"(marge {t['financials']['ebitda_margin']})\n"
                f"  CA {t['financials']['revenue']} ({t['financials']['revenue_growth']})"
            )
        return {"response": "\n".join(lines), "source": "rule-based", "targets_updated": targets_updated}

    # --- Scoring / Methodology queries ---
    if any(w in ql for w in ["score", "methodo", "ponder", "dimension", "calcul", "notation"]):
        lines = ["**Methodologie de scoring EDRCF 6.0 :**\n"]
        lines.append("Le score global (0-100) est calcule sur 5 dimensions :\n")
        for dim, cfg in scoring_config.items():
            dim_signals = [s for s in SIGNAL_CATALOG.values() if s["dimension"] == dim]
            lines.append(
                f"- **{cfg['label']}** (poids {cfg['weight']}%, max {cfg['max']} pts)\n"
                f"  {len(dim_signals)} signaux : "
                + ", ".join(s["label"][:30] for s in dim_signals[:3])
                + ("..." if len(dim_signals) > 3 else "")
            )
        lines.append(
            "\n**Niveaux de priorite :**\n"
            "- **Action Prioritaire** : Score >= 65\n"
            "- **Qualification** : Score 45-64\n"
            "- **Monitoring** : Score 25-44\n"
            "- **Veille Passive** : Score < 25"
        )
        return {"response": "\n".join(lines), "source": "rule-based", "targets_updated": targets_updated}

    # --- Relationship / Network queries ---
    if any(w in ql for w in ["relation", "reseau", "network", "connexion", "banker", "banquier", "approch"]):
        strong = [t for t in enriched_targets if t["relationship"]["strength"] >= 50]
        lines = [f"**{len(strong)} cibles avec relation forte (>= 50%) :**\n"]
        for t in sorted(strong, key=lambda x: x["relationship"]["strength"], reverse=True):
            lines.append(
                f"- **{t['name']}** — Force {t['relationship']['strength']}%\n"
                f"  {t['relationship']['path'][:80]}\n"
                f"  Banquier EDR : {t['relationship']['edr_banker'] or 'Non assigne'}"
            )
        return {"response": "\n".join(lines), "source": "rule-based", "targets_updated": targets_updated}

    # --- Greeting / Help ---
    if any(w in ql for w in ["bonjour", "hello", "salut", "aide", "help", "comment ca"]):
        return {
            "response": (
                f"Bonjour ! Je suis le Copilot IA d'EdRCF 6.0. "
                f"Je surveille actuellement **{len(enriched_targets)} entites** "
                f"a travers **{len(SECTORS_HEAT)} secteurs** en France.\n\n"
                "Voici ce que je peux analyser pour vous :\n\n"
                '- **"Top 5 cibles"** — Les meilleures opportunites\n'
                '- **"Fondateurs > 60 ans"** — Cibles avec dirigeant senior\n'
                '- **"Secteur [nom]"** — Analyse sectorielle\n'
                '- **"[Nom d\'entreprise]"** — Fiche detaillee\n'
                '- **"Pipeline"** — Etat du funnel M&A\n'
                '- **"Signaux"** — Alertes actives\n'
                '- **"LBO / PE"** — Cibles PE-backed\n'
                '- **"Familiales"** — Cibles familiales\n'
                '- **"Scoring"** — Methodologie de notation\n'
                '- **"Relations"** — Reseau et proximite\n'
                '- **"Filtres"** — Options de filtrage'
            ),
            "source": "rule-based",
            "targets_updated": targets_updated,
        }

    # --- Try Pappers search as last resort before default ---
    if len(ql.strip()) > 3:
        try:
            pappers_result = await search_pappers(q)
            if isinstance(pappers_result, dict):
                resultats = pappers_result.get("resultats", [])
                if resultats:
                    lines = [f"**Recherche Pappers pour \"{q}\" — {len(resultats)} resultat(s) :**\n"]
                    for r in resultats[:5]:
                        nom = r.get("nom_entreprise", r.get("denomination", "N/A"))
                        siren = r.get("siren", "")
                        siege = r.get("siege", {})
                        ville = siege.get("ville", "")
                        code_naf = r.get("code_naf", "")
                        libelle_naf = r.get("libelle_code_naf", "")
                        dirigeants = r.get("representants", [])
                        date_crea = r.get("date_creation", "")

                        lines.append(f"**{nom}** (SIREN: {siren})")
                        if ville:
                            lines.append(f"  Siege: {ville}")
                        if libelle_naf:
                            lines.append(f"  Activite: {libelle_naf} ({code_naf})")
                        if date_crea:
                            lines.append(f"  Creation: {date_crea}")
                        if dirigeants:
                            for d in dirigeants[:2]:
                                nom_d = f"{d.get('prenom', '')} {d.get('nom', '')}".strip()
                                qualite = d.get("qualite", "")
                                lines.append(f"  Dirigeant: {nom_d} — {qualite}")
                        lines.append("")
                    lines.append("*Source: Pappers MCP — donnees open data*")
                    return {"response": "\n".join(lines), "source": "pappers-mcp", "targets_updated": targets_updated}
        except Exception as e:
            print(f"[Copilot] Pappers search error: {e}")

    # --- Default fallback ---
    return {
        "response": (
            f"Je surveille actuellement **{len(enriched_targets)} entites** "
            f"a travers **{len(SECTORS_HEAT)} secteurs** en France.\n\n"
            "Voici ce que je peux analyser pour vous :\n\n"
            '- **"Top 5 cibles"** — Les meilleures opportunites\n'
            '- **"Fondateurs > 60 ans"** — Cibles avec dirigeant senior\n'
            '- **"Secteur [nom]"** — Analyse sectorielle detaillee\n'
            '- **"[Nom d\'entreprise]"** — Fiche complete (ex: "Mercier", "DataPulse")\n'
            '- **"Pipeline"** — Etat du funnel M&A\n'
            '- **"Signaux"** — Alertes et detections actives\n'
            '- **"LBO"** — Cibles PE-backed\n'
            '- **"Familiales"** — Entreprises familiales\n'
            '- **"Recherche Pappers"** — Tapez un nom d\'entreprise pour chercher via Pappers\n'
            '- **"Scoring"** — Explication de la methodologie\n'
            '- **"EBITDA"** — Classement financier'
        ),
        "source": "rule-based",
        "targets_updated": targets_updated,
    }


@app.get("/api/graph")
def get_graph():
    """Enhanced network graph: director nodes, cross-mandates, score-based colors, M&A signals."""
    nodes: list = []
    links: list = []
    node_ids: set = set()
    director_companies: dict = {}  # dir_id -> [company_id, ...]

    edr_team = [
        {"id": "edr-1", "name": "Quentin Moreau", "role": "Analyste Senior, EDR CF"},
        {"id": "edr-2", "name": "Manon Lefevre", "role": "Directrice, EDR CF"},
        {"id": "edr-3", "name": "Pierre Legrand", "role": "Banquier Privé, EDR"},
    ]
    for edr in edr_team:
        nodes.append({
            "id": edr["id"], "name": edr["name"], "type": "internal",
            "role": edr["role"], "color": "#6366f1", "score": None,
            "signals_count": 0, "signals": [], "is_holding": False,
            "node_size": 9, "multi_mandats": False,
        })
        node_ids.add(edr["id"])

    top_targets = sorted(enriched_targets, key=lambda x: x["globalScore"], reverse=True)[:12]

    for t in top_targets:
        score = t["globalScore"]
        siren = t.get("siren", "")
        color = "#10b981" if score >= 65 else "#f59e0b" if score >= 45 else "#6366f1" if score >= 25 else "#64748b"
        groupe = t.get("groupe") or t.get("group") or {}
        is_holding = bool(groupe.get("is_holding") or groupe.get("is_group"))
        subsidiaries = groupe.get("entreprises_liees") or groupe.get("subsidiaries") or []
        top_signals = t.get("topSignals", [])

        nodes.append({
            "id": t["id"], "name": t["name"], "type": "company",
            "role": t.get("sector", ""), "color": color, "score": score,
            "priority": t.get("priorityLevel", ""),
            "signals_count": len(top_signals),
            "signals": [s.get("label", "") for s in top_signals[:5]],
            "is_holding": is_holding,
            "sector": t.get("sector", ""), "city": t.get("city", ""),
            "siren": siren,
            "ca": (t.get("financials") or {}).get("revenue", "N/A"),
            "ebitda": (t.get("financials") or {}).get("ebitda", "N/A"),
            "node_size": max(6, min(14, 5 + score // 10)),
            "multi_mandats": False,
        })
        node_ids.add(t["id"])

        for edr in edr_team:
            links.append({"source": edr["id"], "target": t["id"], "label": "Suivi", "value": 1, "type": "follow"})

        for d in t.get("dirigeants", [])[:3]:
            dir_name = (d.get("name") or "").strip()
            if not dir_name or dir_name == t["name"]:
                continue
            dir_age = d.get("age", 0) or 0
            safe = dir_name.lower().replace(" ", "-").replace("'", "").replace("\u2019", "")
            dir_id = f"dir-{safe}"

            if dir_id not in node_ids:
                dir_color = "#ef4444" if dir_age >= 60 else "#f59e0b" if dir_age >= 50 else "#94a3b8"
                nodes.append({
                    "id": dir_id, "name": dir_name, "type": "director",
                    "role": d.get("role", "Dirigeant"), "color": dir_color,
                    "age": dir_age, "age_signal": dir_age >= 60,
                    "score": None, "node_size": 5,
                    "signals_count": 1 if dir_age >= 60 else 0,
                    "signals": ["Fondateur > 60 ans — Signal succession"] if dir_age >= 60 else [],
                    "company": t["name"], "multi_mandats": False, "is_holding": False,
                })
                node_ids.add(dir_id)
                director_companies[dir_id] = [t["id"]]
            else:
                for prev_cid in director_companies.get(dir_id, []):
                    links.append({
                        "source": prev_cid, "target": t["id"],
                        "label": f"Mandat croisé — {dir_name}",
                        "value": 3, "type": "cross_mandate", "director": dir_name,
                    })
                for n in nodes:
                    if n["id"] == dir_id:
                        n["multi_mandats"] = True
                        n["color"] = "#f97316"
                        if "Mandat croisé détecté" not in n["signals"]:
                            n["signals"].append("Mandat croisé détecté")
                            n["signals_count"] += 1
                director_companies.setdefault(dir_id, []).append(t["id"])

            links.append({"source": dir_id, "target": t["id"], "label": d.get("role", "Dirige"), "value": 2, "type": "directs"})

        for i, sub in enumerate(subsidiaries[:2]):
            sub_name = sub if isinstance(sub, str) else (sub.get("denomination") or sub.get("name") or f"Filiale {i+1}")
            sub_id = f"{t['id']}-sub-{i}"
            if sub_id not in node_ids:
                nodes.append({
                    "id": sub_id, "name": sub_name, "type": "subsidiary",
                    "role": f"Filiale de {t['name']}", "color": "#8b5cf6",
                    "score": None, "signals_count": 0, "signals": [],
                    "is_holding": False, "company": t["name"], "node_size": 4, "multi_mandats": False,
                })
                node_ids.add(sub_id)
                links.append({"source": t["id"], "target": sub_id, "label": "Filiale", "value": 1, "type": "subsidiary"})

    cross_mandates_count = sum(1 for l in links if l.get("type") == "cross_mandate")
    return {
        "data": {"nodes": nodes, "links": links},
        "stats": {
            "nodes": len(nodes),
            "links": len(links),
            "companies": sum(1 for n in nodes if n["type"] == "company"),
            "directors": sum(1 for n in nodes if n["type"] == "director"),
            "cross_mandates": cross_mandates_count,
            "signals": sum(n.get("signals_count", 0) for n in nodes),
        },
    }


@app.get("/api/sectors")
def get_sectors():
    return {"data": SECTORS_HEAT}


async def _enrich_with_external_sources(targets: list) -> list:
    """
    Enrich each target with Google News + Infogreffe data.
    Adds news_articles and infogreffe_actes to each company dict,
    so detect_signals() can pick them up during scoring.
    Runs all fetches concurrently with a timeout guard.
    """
    async def _enrich_one(target: dict) -> dict:
        siren = target.get("siren", "")
        name = target.get("name", "")
        enriched = dict(target)
        try:
            news_task = asyncio.create_task(get_google_news(name, max_results=6))
            infogreffe_task = asyncio.create_task(get_infogreffe_actes(siren)) if siren else None

            news = await asyncio.wait_for(news_task, timeout=8)
            actes = []
            if infogreffe_task:
                try:
                    actes = await asyncio.wait_for(infogreffe_task, timeout=7)
                except asyncio.TimeoutError:
                    print(f"[Infogreffe] Timeout for SIREN {siren}")

            enriched["news_articles"] = news
            enriched["infogreffe_actes"] = actes
        except Exception as e:
            print(f"[ExternalEnrich] Error for {name}: {e}")
            enriched.setdefault("news_articles", [])
            enriched.setdefault("infogreffe_actes", [])
        return enriched

    enriched_list = await asyncio.gather(*[_enrich_one(t) for t in targets], return_exceptions=False)
    return list(enriched_list)


@app.post("/api/refresh-targets")
async def refresh_targets():
    """Refresh targets from Papperclip (free gov APIs), then enrich with Google News + Infogreffe."""
    global enriched_targets, raw_targets
    fetched = await load_targets_from_papperclip(count=10)
    if fetched:
        # Enrich with external sources (news + infogreffe actes)
        print(f"[EdRCF] Enriching {len(fetched)} targets with Google News + Infogreffe...")
        fetched = await _enrich_with_external_sources(fetched)
        save_cache(fetched)
        raw_targets = fetched
        enriched_targets = [enrich_target(c) for c in fetched]
        news_count = sum(len(t.get("news_articles", [])) for t in fetched)
        actes_count = sum(len(t.get("infogreffe_actes", [])) for t in fetched)
        return {
            "message": f"{len(enriched_targets)} cibles chargees — {news_count} articles presse, {actes_count} actes Infogreffe",
            "total": len(enriched_targets),
            "news_articles": news_count,
            "infogreffe_actes": actes_count,
        }
    raise HTTPException(500, "Echec du chargement Pappers")


@app.get("/api/admin/refresh-db")
async def admin_refresh_db(
    secret: str = Query(default=""),
    count: int = Query(default=200, ge=10, le=500),
):
    """Cron-safe endpoint: refresh companies from Papperclip + BODACC and save to Supabase.
    Optional: protect with CRON_SECRET env var. count param controls target size (default 200)."""
    cron_secret = os.getenv("CRON_SECRET", "")
    if cron_secret and secret != cron_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")

    global enriched_targets, raw_targets
    try:
        fetched = await load_targets_from_papperclip(count=count)
        if fetched:
            save_cache(fetched)
            await save_to_supabase(fetched)
            raw_targets = fetched
            enriched_targets = [enrich_target(c) for c in fetched]
            return {
                "ok": True,
                "total": len(enriched_targets),
                "message": f"Refreshed {len(enriched_targets)} companies from Papperclip → Supabase",
            }
        raise HTTPException(500, "Papperclip returned no data")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Refresh failed: {e}")


@app.get("/api/admin/load-sector")
async def admin_load_sector(
    naf: str = Query(..., description="NAF code, e.g. 62.01Z"),
    count: int = Query(default=10, ge=1, le=50),
    label: str = Query(default=""),
    secret: str = Query(default=""),
):
    """On-demand: load companies from a specific NAF code and add to the live pool.
    Skips SIRENs already in the pool. Returns the new targets added."""
    cron_secret = os.getenv("CRON_SECRET", "")
    if cron_secret and secret != cron_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")

    global enriched_targets, raw_targets

    existing_sirens = {t.get("siren") for t in raw_targets}
    results = await _papperclip_search(code_naf=naf, per_page=count)

    new_raw: list = []
    for company in results:
        siren = company.get("siren", "")
        if siren and siren not in existing_sirens:
            existing_sirens.add(siren)
            new_raw.append(company)

    if not new_raw:
        return {"added": 0, "total": len(enriched_targets), "message": "No new companies found for this NAF code"}

    new_targets = []
    base_idx = len(raw_targets) + 1
    for i, company in enumerate(new_raw):
        siren = company.get("siren", "")
        try:
            company_info = await _papperclip_get_company(siren)
            if not company_info:
                continue
            target = build_target(idx=base_idx + i, company_info=company_info, search_info=company)
            new_targets.append(target)
        except Exception as e:
            print(f"[load-sector] Error for {siren}: {e}")

    if new_targets:
        async with _targets_lock:
            raw_targets.extend(new_targets)
            new_enriched = [enrich_target(c) for c in new_targets]
            enriched_targets.extend(new_enriched)
        await save_to_supabase(new_targets)

    return {
        "added": len(new_targets),
        "total": len(enriched_targets),
        "sector_label": label or naf,
        "companies": [{"name": t["name"], "siren": t["siren"], "score": t.get("globalScore", 0)} for t in new_targets],
    }


# =============================================================================
# Admin helpers
# =============================================================================

_SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
_SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


def _check_admin_secret(secret: str):
    """Vérifie le secret admin. Passe si CRON_SECRET n'est pas configuré."""
    cron_secret = os.getenv("CRON_SECRET", "")
    if cron_secret and secret != cron_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _supabase_headers_main() -> dict:
    return {
        "apikey": _SUPABASE_KEY,
        "Authorization": f"Bearer {_SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


# NOTE: /api/admin/bronze-stats, /load-bronze, /load-bodacc, /load-rne,
#       /load-pappers, /run-all → voir routers/admin.py (inclus ci-dessus)


# =============================================================================
# /api/admin/index-stats — Stats de sirene_index
# =============================================================================

@app.get("/api/admin/index-stats")
async def admin_index_stats(secret: str = Query(default="")):
    """Stats de la table sirene_index Supabase (index 16M SIRENE)."""
    _check_admin_secret(secret)

    if not _SUPABASE_URL or not _SUPABASE_KEY:
        return {"configured": False, "message": "Supabase non configuré (SUPABASE_URL / SUPABASE_KEY)"}

    stats: dict = {"configured": True}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            for label, extra_params in [
                ("total_indexed",   {}),
                ("enriched",        {"enriched": "eq.true"}),
                ("to_enrich",       {"enriched": "eq.false"}),
                ("bodacc_hot",      {"bodacc_recent": "eq.true"}),
                ("high_score_60p",  {"ma_score_estimate": "gte.60"}),
            ]:
                r = await client.get(
                    f"{_SUPABASE_URL}/rest/v1/sirene_index",
                    params={"select": "count", **extra_params},
                    headers={**_supabase_headers_main(), "Prefer": "count=exact"},
                )
                content_range = r.headers.get("content-range", "0/0")
                stats[label] = int(content_range.split("/")[-1])
    except Exception as e:
        stats["error"] = str(e)

    stats["enriched_targets_in_memory"] = len(enriched_targets)
    return stats


# =============================================================================
# /api/admin/rebuild-index — Lance le pipeline SIRENE
# =============================================================================

@app.get("/api/admin/rebuild-index")
async def admin_rebuild_index(
    background_tasks: BackgroundTasks,
    mode: str = Query(
        default="api",
        description="'api' = sweep paginé Vercel-safe | 'bulk' = dl SIRENE complet (local uniquement)",
    ),
    depts: str = Query(
        default="",
        description="Départements séparés par virgule, ex: 75,69,13 (mode api uniquement)",
    ),
    secret: str = Query(default=""),
):
    """Lance le rebuild de sirene_index.

    mode=api  : sweep via API Recherche Entreprises — fonctionne sur Vercel.
                Couvre les grands départements × 62 codes NAF.
                Durée estimée : 20-60 min selon le nb de depts.

    mode=bulk : télécharge le fichier SIRENE INSEE complet (~2.5 Go) et filtre
                localement. Uniquement pour usage local ou VPS (pas Vercel).
                Durée estimée : 15-25 min. Produit 50 000-80 000 SIRENs.
    """
    _check_admin_secret(secret)

    dept_list = [d.strip() for d in depts.split(",") if d.strip()] if depts else []

    if mode == "bulk":
        try:
            from sirene_bulk import run_full_rebuild
            background_tasks.add_task(run_full_rebuild)
            return {
                "status": "started",
                "mode": "bulk",
                "message": (
                    "Téléchargement SIRENE complet lancé en background (~20 min). "
                    "Suivre la progression dans les logs serveur."
                ),
            }
        except ImportError:
            raise HTTPException(500, "sirene_bulk.py introuvable dans le PATH")

    # mode=api (défaut — Vercel-safe)
    try:
        from sirene_bulk import api_mode_sweep
        background_tasks.add_task(api_mode_sweep, dept_list or None, 25)
        return {
            "status": "started",
            "mode": "api",
            "depts": dept_list if dept_list else "20 grands départements par défaut",
            "naf_codes": 62,
            "message": (
                "Sweep API lancé en background. "
                "Vérifier /api/admin/index-stats pour suivre la progression."
            ),
        }
    except ImportError:
        raise HTTPException(500, "sirene_bulk.py introuvable dans le PATH")


# =============================================================================
# /api/admin/enrich-batch — Enrichit N entreprises depuis sirene_index
# =============================================================================

@app.get("/api/admin/enrich-batch")
async def admin_enrich_batch(
    n: int = Query(default=20, ge=1, le=100, description="Nb d'entreprises à enrichir (max 100)"),
    priority: str = Query(
        default="score",
        description="'score' (ma_score_estimate DESC) | 'bodacc' (BODACC hot en priorité) | 'fifo' (created_at ASC)",
    ),
    secret: str = Query(default=""),
):
    """Enrichit N entreprises depuis sirene_index (non encore enrichies).

    Chaque enrichissement appelle get_full_company_info() → build_target() → Supabase.
    Rate-limited à ~5 req/s pour respecter les quotas API gouvernementaux.
    Les nouvelles cibles sont immédiatement disponibles dans /api/targets.
    """
    _check_admin_secret(secret)

    if not _SUPABASE_URL or not _SUPABASE_KEY:
        raise HTTPException(400, "Supabase non configuré — impossible de lire sirene_index")

    global enriched_targets, raw_targets

    # ── 1. Récupérer les SIRENs candidats depuis sirene_index ────────────
    order_map = {
        "score":  "ma_score_estimate.desc",
        "bodacc": "bodacc_recent.desc,ma_score_estimate.desc",
        "fifo":   "created_at.asc",
    }
    order_clause = order_map.get(priority, "ma_score_estimate.desc")

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{_SUPABASE_URL}/rest/v1/sirene_index",
                params={
                    "enriched": "eq.false",
                    "select": "siren,denomination,naf,dept,ma_score_estimate,bodacc_recent",
                    "order": order_clause,
                    "limit": n,
                },
                headers=_supabase_headers_main(),
            )
            if r.status_code != 200:
                raise HTTPException(500, f"Supabase error HTTP {r.status_code}")
            candidates = r.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur lecture sirene_index: {e}")

    if not candidates:
        return {
            "enriched": 0,
            "total_in_memory": len(enriched_targets),
            "message": "Aucun SIREN à enrichir dans sirene_index (tous déjà enrichis ou index vide).",
        }

    # ── 2. Enrichissement de chaque candidat ─────────────────────────────
    existing_sirens = {t.get("siren") for t in raw_targets}
    results: dict = {"enriched": 0, "skipped": 0, "failed": 0, "new_targets": []}

    for candidate in candidates:
        siren = candidate["siren"]

        # Skip si déjà en mémoire
        if siren in existing_sirens:
            results["skipped"] += 1
            _mark_enriched_in_index(siren)  # corriger l'index
            continue

        try:
            company_info = await _papperclip_get_company(siren)
            if not company_info:
                results["failed"] += 1
                continue

            target = build_target(
                idx=len(raw_targets) + 1,
                company_info=company_info,
                search_info={
                    "siren": siren,
                    "nom_entreprise": candidate.get("denomination", ""),
                    "code_naf": candidate.get("naf", ""),
                },
            )

            async with _targets_lock:
                raw_targets.append(target)
                enriched = enrich_target(target)
                enriched_targets.append(enriched)
                existing_sirens.add(siren)

            results["enriched"] += 1
            results["new_targets"].append({
                "name":    target["name"],
                "siren":   siren,
                "score":   target.get("globalScore", 0),
                "signals": len(target.get("active_signals", [])),
                "dept":    candidate.get("dept", ""),
                "naf":     candidate.get("naf", ""),
            })

            # Marquer enrichi dans sirene_index
            asyncio.create_task(_mark_enriched_in_index(siren))

        except Exception as e:
            print(f"[enrich-batch] Erreur {siren}: {e}")
            results["failed"] += 1

        await asyncio.sleep(0.2)  # ~5 req/s

    # ── 3. Sauvegarder les nouvelles cibles en Supabase ─────────────────
    if results["enriched"] > 0:
        new_sirens = {t["siren"] for t in results["new_targets"]}
        new_raw = [t for t in raw_targets if t.get("siren") in new_sirens]
        await save_to_supabase(new_raw)

    results["total_in_memory"] = len(enriched_targets)
    return results


async def _mark_enriched_in_index(siren: str):
    """Marque un SIREN comme enrichi dans sirene_index (fire-and-forget)."""
    if not _SUPABASE_URL or not _SUPABASE_KEY:
        return
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            await client.patch(
                f"{_SUPABASE_URL}/rest/v1/sirene_index?siren=eq.{siren}",
                json={"enriched": True, "enriched_at": datetime.utcnow().isoformat()},
                headers={**_supabase_headers_main(), "Prefer": "resolution=merge-duplicates"},
            )
    except Exception:
        pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
