"""
EdRCF 6.0 — Papperclip: Free Government Data Sources
Replaces paid Pappers MCP with free French government APIs.

Sources:
  - API Recherche Entreprises (gouv.fr) — no auth, 7 req/s
  - BODACC (OpenDataSoft) — no auth, legal announcements
"""

import os
import httpx
from datetime import datetime

# ==========================================================================
# Constants
# ==========================================================================

RECHERCHE_API = "https://recherche-entreprises.api.gouv.fr/search"
BODACC_API = "https://bodacc-datadila.opendatasoft.com/api/records/1.0/search/"

_current_year = datetime.now().year


# ==========================================================================
# API Recherche Entreprises (Primary Source)
# ==========================================================================

async def fetch_company_from_gouv(siren: str) -> dict | None:
    """Fetch a single company by SIREN from API Recherche Entreprises.
    Returns data in Pappers-compatible format for build_target()."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(RECHERCHE_API, params={"q": siren})
            if resp.status_code != 200:
                print(f"[Papperclip] Recherche API error: HTTP {resp.status_code}")
                return None
            data = resp.json()
            results = data.get("results", [])
            if not results:
                print(f"[Papperclip] No results for SIREN {siren}")
                return None
            # Find exact SIREN match
            company = None
            for r in results:
                if r.get("siren") == siren:
                    company = r
                    break
            if not company:
                company = results[0]
            return _map_gouv_to_pappers(company)
    except Exception as e:
        print(f"[Papperclip] Recherche API exception: {e}")
        return None


async def search_companies_gouv(
    query: str = "",
    code_naf: str = "",
    departement: str = "",
    tranche_effectif: str = "",
    page: int = 1,
    per_page: int = 10,
) -> list[dict]:
    """Search companies from API Recherche Entreprises.
    Returns list of Pappers-compatible company dicts."""
    params: dict = {"page": page, "per_page": per_page}
    if query:
        params["q"] = query
    if code_naf:
        params["activite_principale"] = code_naf
    if departement:
        params["departement"] = departement
    if tranche_effectif:
        params["tranche_effectif_salarie"] = tranche_effectif

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(RECHERCHE_API, params=params)
            if resp.status_code != 200:
                print(f"[Papperclip] Search error: HTTP {resp.status_code}")
                return []
            data = resp.json()
            results = data.get("results", [])
            return [_map_gouv_to_pappers(r) for r in results]
    except Exception as e:
        print(f"[Papperclip] Search exception: {e}")
        return []


def _map_gouv_to_pappers(company: dict) -> dict:
    """Map API Recherche Entreprises response to Pappers-compatible format.
    This is the critical mapping that makes detect_signals() and
    build_target() work without modification."""
    siege = company.get("siege", {}) or {}
    dirigeants_raw = company.get("dirigeants", []) or []
    finances_raw = company.get("finances", {}) or {}

    # --- Map dirigeants to Pappers 'representants' format ---
    representants = []
    for d in dirigeants_raw:
        rep = {
            "prenom": d.get("prenoms", "") or d.get("prenom", ""),
            "nom": d.get("nom", "") or d.get("denomination", ""),
            "qualite": d.get("qualite", ""),
            "age": 0,
            "date_de_naissance": "",
        }
        # Calculate age from annee_de_naissance or date_de_naissance
        annee = d.get("annee_de_naissance")
        date_naissance = d.get("date_de_naissance", "")
        if annee:
            rep["age"] = _current_year - int(annee)
            rep["date_de_naissance"] = f"{annee}-01-01"
        elif date_naissance:
            rep["date_de_naissance"] = date_naissance
            try:
                birth_year = int(str(date_naissance)[:4])
                rep["age"] = _current_year - birth_year
            except (ValueError, IndexError):
                pass
        representants.append(rep)

    # --- Map finances to Pappers format ---
    # API returns: {"2024": {"ca": 123456, "resultat_net": 789}, "2023": {...}}
    finances = []
    for year_str in sorted(finances_raw.keys(), reverse=True):
        year_data = finances_raw[year_str]
        if isinstance(year_data, dict):
            finances.append({
                "annee": int(year_str),
                "chiffre_affaires": year_data.get("ca", 0) or 0,
                "resultat": year_data.get("resultat_net", 0) or 0,
            })

    # --- Map etablissements count ---
    nb_etab = company.get("nombre_etablissements_ouverts", 1) or 1
    etablissements = [{"siret": siege.get("siret", "")}] * nb_etab

    # --- Map nature_juridique to forme_juridique text ---
    nature_juridique = company.get("nature_juridique", "")
    forme_juridique = _nature_juridique_to_text(nature_juridique)

    # --- Map tranche_effectif to effectif string ---
    effectif = _tranche_to_effectif(
        siege.get("tranche_effectif_salarie", "")
    )

    # --- Direct CA / resultat for endpoint compatibility ---
    ca_recent = finances[0]["chiffre_affaires"] if finances else 0
    resultat_recent = finances[0]["resultat"] if finances else 0

    # --- Departement from code_postal ---
    cp = siege.get("code_postal", "") or ""
    departement = cp[:2] if len(cp) >= 2 else ""

    # --- Build Pappers-compatible dict ---
    return {
        "siren": company.get("siren", ""),
        "nom_entreprise": company.get("nom_complet", "") or company.get("nom_raison_sociale", ""),
        "siege": {
            "adresse": siege.get("adresse", ""),
            "code_postal": cp,
            "ville": siege.get("commune", ""),
            "siret": siege.get("siret", ""),
            "departement": departement,
        },
        "code_naf": siege.get("activite_principale", "") or company.get("activite_principale", ""),
        "libelle_code_naf": siege.get("libelle_activite_principale", "") or "",
        "chiffre_affaires": ca_recent,
        "resultat": resultat_recent,
        "date_creation": company.get("date_creation", ""),
        "forme_juridique": forme_juridique,
        "effectif": effectif,
        "representants": representants,
        "finances": finances,
        "etablissements": etablissements,
        "entreprise_cessee": company.get("etat_administratif") == "F",
        "date_cessation": company.get("date_fermeture"),
        "statut_activite": "Radie" if company.get("etat_administratif") == "F" else "En activite",
        "categorie_entreprise": company.get("categorie_entreprise", ""),
        # Fields that free API doesn't provide (set to empty)
        "beneficiaires_effectifs": [],
        "publications_bodacc": [],  # Filled by fetch_bodacc()
        "procedures_collectives": [],
        "procedure_collective_en_cours": False,
        "procedure_collective_existe": False,
        "scoring_non_financier": None,
        "infogreffe_actes": [],  # Filled by existing /api/infogreffe endpoint
        "news_articles": [],  # Filled by existing /api/news endpoint
    }


# ==========================================================================
# BODACC (Legal Announcements)
# ==========================================================================

async def fetch_bodacc(siren: str) -> list[dict]:
    """Fetch BODACC announcements for a company.
    Returns list in Pappers publications_bodacc format."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(BODACC_API, params={
                "dataset": "annonces-commerciales",
                "q": siren,
                "rows": 20,
                "sort": "-dateparution",
            })
            if resp.status_code != 200:
                print(f"[Papperclip] BODACC error: HTTP {resp.status_code}")
                return []
            data = resp.json()
            records = data.get("records", [])
            publications = []
            for rec in records:
                fields = rec.get("fields", {})
                pub_type = _bodacc_type(fields)
                publications.append({
                    "type": pub_type,
                    "date": fields.get("dateparution", ""),
                    "description": fields.get("modificationsgenerales", "")
                                   or fields.get("familleavis_lib", ""),
                    "administration": "",
                })
            return publications
    except Exception as e:
        print(f"[Papperclip] BODACC exception: {e}")
        return []


def _bodacc_type(fields: dict) -> str:
    """Map BODACC familleavis to Pappers-compatible type string."""
    famille = (fields.get("familleavis", "") or "").lower()
    modifs = (fields.get("modificationsgenerales", "") or "").lower()
    lib = (fields.get("familleavis_lib", "") or "").lower()
    combined = f"{famille} {modifs} {lib}"

    if "vente" in combined or "cession" in combined:
        return "Vente"
    if "radiation" in combined:
        return "Radiation"
    if "capital" in combined:
        return "Modification"
    if "depot" in combined or "dpc" in famille:
        return "Depot des comptes"
    if "modification" in combined:
        return "Modification"
    if "immatriculation" in combined:
        return "Immatriculation"
    if "dissolution" in combined or "liquidation" in combined:
        return "Radiation"
    return "Modification"


# ==========================================================================
# INPI RNE (Director registry — optional OAuth2 credentials)
# ==========================================================================

_INPI_TOKEN: str | None = None
_INPI_TOKEN_EXPIRY: float = 0.0

INPI_LOGIN_URL = "https://registre-national-entreprises.inpi.fr/api/sso/login"
INPI_COMPANIES_URL = "https://registre-national-entreprises.inpi.fr/api/companies"


async def _get_inpi_token() -> str | None:
    """Fetch INPI OAuth2 token. Returns None if INPI_USER / INPI_PASSWORD not set."""
    import time
    global _INPI_TOKEN, _INPI_TOKEN_EXPIRY

    user = os.environ.get("INPI_USER", "")
    password = os.environ.get("INPI_PASSWORD", "")
    if not user or not password:
        return None

    if _INPI_TOKEN and time.time() < _INPI_TOKEN_EXPIRY:
        return _INPI_TOKEN

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                INPI_LOGIN_URL,
                json={"username": user, "password": password},
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                _INPI_TOKEN = data.get("token")
                _INPI_TOKEN_EXPIRY = time.time() + 3500  # token valid ~1h
                print(f"[INPI] Token obtained")
                return _INPI_TOKEN
            print(f"[INPI] Login failed: HTTP {resp.status_code}")
    except Exception as e:
        print(f"[INPI] Token error: {e}")
    return None


async def fetch_inpi_rne(siren: str) -> dict | None:
    """Fetch company data from INPI RNE API.
    Returns raw INPI data dict or None if unavailable / not configured."""
    token = await _get_inpi_token()
    if not token:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{INPI_COMPANIES_URL}/{siren}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 200:
                return resp.json()
            print(f"[INPI] RNE fetch HTTP {resp.status_code} for {siren}")
    except Exception as e:
        print(f"[INPI] RNE error for {siren}: {e}")
    return None


def _enrich_representants_from_inpi(representants: list, inpi_data: dict) -> list:
    """Merge INPI RNE director data into existing representants list.
    Adds: historical mandates, more precise age, nationality."""
    if not inpi_data:
        return representants

    # INPI structure varies — try common paths
    inpi_reps = (
        inpi_data.get("representants")
        or inpi_data.get("dirigeants")
        or []
    )
    if not inpi_reps:
        # Try nested structure
        formality = inpi_data.get("formality") or {}
        content = formality.get("content") or {}
        inpi_reps = content.get("personnesMorales", []) or content.get("personneMorale", [])

    # Build a name-keyed map for merging
    inpi_map: dict = {}
    for r in inpi_reps:
        nom = (r.get("nom") or r.get("lastName") or "").upper()
        if nom:
            inpi_map[nom] = r

    enriched = []
    for rep in representants:
        nom_key = (rep.get("nom") or "").upper()
        inpi_match = inpi_map.get(nom_key)
        if inpi_match:
            rep = dict(rep)
            # Add nationality if present
            nat = inpi_match.get("nationalite") or inpi_match.get("nationality")
            if nat:
                rep["nationalite"] = nat
            # Add more precise birth date if INPI has it
            if not rep.get("date_de_naissance"):
                dob = inpi_match.get("dateDeNaissance") or inpi_match.get("birthDate")
                if dob:
                    rep["date_de_naissance"] = str(dob)[:10]
                    try:
                        rep["age"] = _current_year - int(str(dob)[:4])
                    except Exception:
                        pass
        enriched.append(rep)
    return enriched


async def enrich_with_cross_mandates(siren: str, representants: list) -> list:
    """For the first 3 directors, search for other companies they manage.
    Populates 'autres_mandats' — used by detect_signals() for dirigeant_multi_mandats."""
    enriched = []
    for idx, rep in enumerate(representants):
        if idx >= 3:  # Only enrich top 3 to respect rate limits
            enriched.append(rep)
            continue
        nom = (rep.get("nom") or "").strip()
        prenom = (rep.get("prenom") or "").strip()
        if not nom:
            enriched.append(rep)
            continue
        query = f"{prenom} {nom}".strip()
        try:
            companies = await search_companies_gouv(query=query, per_page=5)
            autres = [
                {"entreprise": {"nom_entreprise": c.get("nom_entreprise", ""), "siren": c.get("siren", "")}}
                for c in companies
                if c.get("siren") and c.get("siren") != siren
            ][:3]
            rep = dict(rep)
            rep["autres_mandats"] = autres
        except Exception:
            rep = dict(rep)
            rep.setdefault("autres_mandats", [])
        enriched.append(rep)
    return enriched + representants[3:]


# ==========================================================================
# Aggregate all sources into a single company_info
# ==========================================================================

async def get_full_company_info(siren: str) -> dict | None:
    """Fetch and aggregate data from all free sources for a given SIREN.
    Returns a complete company_info dict compatible with build_target()
    and detect_signals().

    Performance (audit PERF-5) : les 3 fetches indépendants (gouv, BODACC,
    INPI) sont parallélisés via asyncio.gather — gain p95 ~1-2s sur les
    chaînes /api/pappers/* et /copilot/*. cross-mandates reste séquentiel
    car dépend des representants retournés par fetch_company_from_gouv.
    """
    import asyncio

    # 3 fetches indépendants en parallèle (chacun a son propre timeout)
    results = await asyncio.gather(
        fetch_company_from_gouv(siren),
        fetch_bodacc(siren),
        fetch_inpi_rne(siren),
        return_exceptions=True,
    )
    company_info, bodacc, inpi_data = results

    # gouv est la source primaire — sans elle on abandonne
    if not company_info or isinstance(company_info, Exception):
        return None

    # BODACC : enrichit signaux + détecte procédures collectives
    if bodacc and not isinstance(bodacc, Exception):
        company_info["publications_bodacc"] = bodacc
        for pub in bodacc:
            desc = (pub.get("description") or "").lower()
            pub_type = (pub.get("type") or "").lower()
            if any(w in f"{desc} {pub_type}" for w in [
                "redressement", "liquidation judiciaire", "sauvegarde",
                "procedure collective"
            ]):
                company_info["procedure_collective_en_cours"] = True
                company_info["procedure_collective_existe"] = True
                company_info["procedures_collectives"] = [pub]
                break
    else:
        bodacc = []  # pour le print final ne pas crasher

    # INPI RNE : enrichissement representants (optionnel — requires creds)
    if inpi_data and not isinstance(inpi_data, Exception) and company_info.get("representants"):
        company_info["representants"] = _enrich_representants_from_inpi(
            company_info["representants"], inpi_data
        )
        company_info["inpi_rne_raw"] = inpi_data  # store for audit

    # Cross-mandate enrichment (séquentiel : a besoin des representants enrichis ci-dessus)
    if company_info.get("representants"):
        company_info["representants"] = await enrich_with_cross_mandates(
            siren, company_info["representants"]
        )

    print(f"[Papperclip] Aggregated data for {company_info.get('nom_entreprise', siren)}: "
          f"{len(company_info.get('representants', []))} dirigeants, "
          f"{len(company_info.get('finances', []))} exercices, "
          f"{len(bodacc)} annonces BODACC")

    return company_info


async def search_and_enrich(
    query: str = "",
    code_naf: str = "",
    departement: str = "",
    count: int = 10,
) -> list[dict]:
    """Search companies and enrich each with BODACC data.
    Returns list of Pappers-compatible company_info dicts."""
    companies = await search_companies_gouv(
        query=query,
        code_naf=code_naf,
        departement=departement,
        per_page=min(count, 25),
    )
    enriched = []
    for company in companies:
        siren = company.get("siren", "")
        if siren:
            bodacc = await fetch_bodacc(siren)
            if bodacc:
                company["publications_bodacc"] = bodacc
        enriched.append(company)
    return enriched


# ==========================================================================
# Helper mappings
# ==========================================================================

def _nature_juridique_to_text(code: str) -> str:
    """Map nature_juridique code to human-readable text."""
    if not code:
        return ""
    code = str(code)
    mapping = {
        "1000": "Entrepreneur individuel",
        "5498": "SAS",
        "5499": "SAS unipersonnelle (SASU)",
        "5710": "SAS",
        "5720": "SASU",
        "5410": "SARL",
        "5422": "SARL unipersonnelle (EURL)",
        "5599": "SA a conseil d'administration",
        "5505": "SA a directoire",
        "5510": "SA a conseil d'administration",
        "5699": "SA a directoire",
        "6540": "SCI",
        "5307": "SNC",
        "9220": "Association declaree",
        "9221": "Association declaree reconnue d'utilite publique",
    }
    return mapping.get(code, f"Forme juridique {code}")


_TRANCHE_MAP = {
    "00": "0",
    "01": "1-2",
    "02": "3-5",
    "03": "6-9",
    "11": "10-19",
    "12": "20-49",
    "21": "50-99",
    "22": "100-199",
    "31": "200-249",
    "32": "250-499",
    "41": "500-999",
    "42": "1000-1999",
    "51": "2000-4999",
    "52": "5000-9999",
    "53": "10000+",
}


def _tranche_to_effectif(tranche: str) -> str:
    """Map tranche_effectif_salarie code to readable range."""
    if not tranche:
        return "N/A"
    return _TRANCHE_MAP.get(str(tranche), str(tranche))


# ==========================================================================
# Startup pipeline: load initial targets from free sources
# ==========================================================================

# Search profiles — NAF codes × per_page target = ~300 unique companies
# Each profile runs one API call (7 req/s limit, fully respected)
_LOAD_PROFILES = [
    # ── Courtage / Assurance (heat 91) ───────────────────────────────
    {"label": "Courtage assurance",              "code_naf": "66.22Z", "per_page": 8},
    {"label": "Activites auxiliaires assurance", "code_naf": "66.29Z", "per_page": 6},
    {"label": "Gestion de fonds",                "code_naf": "64.30Z", "per_page": 5},
    {"label": "Gestion patrimoine conseil",      "code_naf": "66.30Z", "per_page": 5},
    # ── Holding / Gestion actifs ──────────────────────────────────────
    {"label": "Holding gestion actifs",          "code_naf": "64.20Z", "per_page": 6},
    {"label": "Activites fiduciaires",           "code_naf": "64.19Z", "per_page": 4},
    # ── Logistique / Transport ────────────────────────────────────────
    {"label": "Transport routier fret",          "code_naf": "49.41A", "per_page": 6},
    {"label": "Transport express messagerie",    "code_naf": "49.41B", "per_page": 5},
    {"label": "Entreposage logistique",          "code_naf": "52.10B", "per_page": 5},
    {"label": "Affrètement / organisation tpt",  "code_naf": "52.29A", "per_page": 4},
    # ── BTP / Construction ────────────────────────────────────────────
    {"label": "Construction batiments",          "code_naf": "41.20A", "per_page": 6},
    {"label": "Travaux installation electrique", "code_naf": "43.21A", "per_page": 5},
    {"label": "Travaux plomberie CVC",           "code_naf": "43.22A", "per_page": 4},
    {"label": "Travaux gros oeuvre",             "code_naf": "43.99C", "per_page": 4},
    {"label": "Construction immeubles",          "code_naf": "41.10A", "per_page": 4},
    # ── Services B2B / Conseil ────────────────────────────────────────
    {"label": "Conseil management",              "code_naf": "70.22Z", "per_page": 7},
    {"label": "Activites comptabilite audit",    "code_naf": "69.20Z", "per_page": 6},
    {"label": "Conseil juridique",               "code_naf": "69.10Z", "per_page": 5},
    {"label": "Recrutement RH",                  "code_naf": "78.10Z", "per_page": 5},
    {"label": "Services securite",               "code_naf": "80.10Z", "per_page": 4},
    {"label": "Nettoyage batiments",             "code_naf": "81.21Z", "per_page": 4},
    {"label": "Services facilities management",  "code_naf": "81.10Z", "per_page": 4},
    # ── MedTech / Sante ───────────────────────────────────────────────
    {"label": "Fabrication materiel medical",    "code_naf": "32.50A", "per_page": 5},
    {"label": "Cliniques et hopitaux prives",    "code_naf": "86.10Z", "per_page": 4},
    {"label": "Pharmacies de detail",            "code_naf": "47.73Z", "per_page": 4},
    {"label": "Fabrication produits pharma",     "code_naf": "21.20Z", "per_page": 4},
    {"label": "Analyses medecine",               "code_naf": "86.90B", "per_page": 3},
    # ── Industrie / Tech ──────────────────────────────────────────────
    {"label": "Fabrication machines ind.",       "code_naf": "28.99B", "per_page": 5},
    {"label": "Fabrication composants electro.", "code_naf": "26.11Z", "per_page": 4},
    {"label": "Fabrication équipements auto",    "code_naf": "29.32Z", "per_page": 4},
    {"label": "Metallurgie / fonderie",          "code_naf": "24.52Z", "per_page": 4},
    {"label": "Chaudronnerie serrurerie",        "code_naf": "25.12Z", "per_page": 4},
    {"label": "Fabrication emballage metal",     "code_naf": "25.91Z", "per_page": 3},
    # ── IT / SaaS / Digital ───────────────────────────────────────────
    {"label": "Activités informatiques",         "code_naf": "62.01Z", "per_page": 6},
    {"label": "Conseil systemes informatiques",  "code_naf": "62.02A", "per_page": 5},
    {"label": "Edition logiciels applicatifs",   "code_naf": "58.29C", "per_page": 5},
    {"label": "Portails internet",               "code_naf": "63.12Z", "per_page": 4},
    # ── Agroalimentaire ───────────────────────────────────────────────
    {"label": "Industrie agroalimentaire",       "code_naf": "10.89Z", "per_page": 5},
    {"label": "Fabrication vins / spiritueux",   "code_naf": "11.02A", "per_page": 4},
    {"label": "Boulangerie / Patisserie indus.",  "code_naf": "10.71A", "per_page": 4},
    {"label": "Transformation viandes",          "code_naf": "10.11Z", "per_page": 3},
    # ── Energie / CleanTech ───────────────────────────────────────────
    {"label": "Production energie renouvelable", "code_naf": "35.11Z", "per_page": 5},
    {"label": "Services efficacite energetique", "code_naf": "71.12B", "per_page": 4},
    {"label": "Recuperation materiaux valorises","code_naf": "38.31Z", "per_page": 4},
    {"label": "Traitement eaux usees",           "code_naf": "37.00Z", "per_page": 3},
    # ── Commerce de gros / Distribution ──────────────────────────────
    {"label": "Commerce gros produits indus.",   "code_naf": "46.69Z", "per_page": 5},
    {"label": "Commerce gros equipement ind.",   "code_naf": "46.63Z", "per_page": 4},
    {"label": "Commerce gros alimentation",      "code_naf": "46.39B", "per_page": 4},
    {"label": "Commerce gros medicaments",       "code_naf": "46.46Z", "per_page": 4},
    # ── Tourisme / Hotellerie ─────────────────────────────────────────
    {"label": "Hotellerie de plein air",         "code_naf": "55.30Z", "per_page": 4},
    {"label": "Hotels classiques",               "code_naf": "55.10Z", "per_page": 4},
    {"label": "Restaurants gastronomiques",      "code_naf": "56.10A", "per_page": 4},
    # ── Immobilier ────────────────────────────────────────────────────
    {"label": "Promotion immobiliere",           "code_naf": "41.10B", "per_page": 5},
    {"label": "Administration biens immobiliers","code_naf": "68.32A", "per_page": 4},
    # ── Education / Formation ─────────────────────────────────────────
    {"label": "Formation professionnelle",       "code_naf": "85.59B", "per_page": 5},
    {"label": "Enseignement superieur prive",    "code_naf": "85.42Z", "per_page": 4},
    # ── Auto / Mobility ───────────────────────────────────────────────
    {"label": "Commerce vehicules neufs",        "code_naf": "45.11Z", "per_page": 4},
    {"label": "Reparation vehicules",            "code_naf": "45.20A", "per_page": 4},
    # ── Communication / Media ─────────────────────────────────────────
    {"label": "Relations publiques / RP",        "code_naf": "73.11Z", "per_page": 4},
    {"label": "Edition revues et periodiques",   "code_naf": "58.14Z", "per_page": 3},
    # ── Aeronautique / Defense ────────────────────────────────────────
    {"label": "Construction aeronefs",           "code_naf": "30.30Z", "per_page": 3},
    {"label": "Fabrication equipements defense", "code_naf": "30.40Z", "per_page": 3},
]


async def load_bodacc_hot_sirens(rows: int = 100) -> list[str]:
    """Fetch SIRENs from BODACC with recent M&A-relevant announcements.

    Targets: cession de fonds + modification de dirigeant (last 90 days).
    These companies carry the strongest M&A signals.
    """
    sirens: list[str] = []
    seen: set[str] = set()

    queries = [
        "typeavis_lib:Cession",
        "typeavis_lib:Modification",
    ]

    async with httpx.AsyncClient(timeout=15) as client:
        for q in queries:
            if len(sirens) >= rows:
                break
            try:
                resp = await client.get(
                    BODACC_API,
                    params={
                        "dataset": "annonces-commerciales",
                        "q": q,
                        "sort": "dateparution",
                        "rows": min(rows, 50),
                        "fields": "siren,typeavis_lib,dateparution",
                    },
                )
                if resp.status_code != 200:
                    continue
                records = resp.json().get("records", [])
                for rec in records:
                    siren = str(rec.get("fields", {}).get("siren", "")).strip()
                    if siren and len(siren) == 9 and siren not in seen:
                        seen.add(siren)
                        sirens.append(siren)
            except Exception as e:
                print(f"[BODACC-bulk] Error for query '{q}': {e}")

    print(f"[BODACC-bulk] Found {len(sirens)} hot SIRENs from recent announcements")
    return sirens


async def load_targets_from_papperclip(count: int = 200, include_bodacc: bool = True) -> list:
    """Load M&A target companies from free government APIs.

    Pipeline:
      1. NAF-profile search (60 profiles × per_page) → base universe
      2. BODACC hot-SIRENs (recent cessions/modifications) → signal-rich additions
      3. Deduplication → enrich with BODACC publications → build_target()

    count: max total targets to build (default 200)
    include_bodacc: also load companies from recent BODACC events
    """
    from pappers_loader import build_target  # local import to avoid circular at module level

    seen_sirens: set = set()
    raw_companies: list = []   # list of search-info dicts

    print(f"[Papperclip] Starting load pipeline (target: {count} companies)...")

    # ── Phase 1: NAF profile search ──────────────────────────────────
    for profile in _LOAD_PROFILES:
        if len(raw_companies) >= count:
            break
        label = profile["label"]
        code_naf = profile.get("code_naf", "")
        per_page = min(profile.get("per_page", 5), 25)  # API max 25
        try:
            results = await search_companies_gouv(code_naf=code_naf, per_page=per_page)
            added = 0
            for company in results:
                siren = company.get("siren", "")
                if siren and siren not in seen_sirens:
                    seen_sirens.add(siren)
                    raw_companies.append(company)
                    added += 1
                    if len(raw_companies) >= count:
                        break
            if added:
                print(f"[Papperclip] {label}: +{added} (pool {len(raw_companies)})")
        except Exception as e:
            print(f"[Papperclip] Search error for {label}: {e}")

    # ── Phase 2: BODACC hot SIRENs (cession / modification dirigeant) ─
    if include_bodacc and len(raw_companies) < count:
        remaining = count - len(raw_companies)
        hot_sirens = await load_bodacc_hot_sirens(rows=min(remaining + 20, 100))
        bodacc_added = 0
        for siren in hot_sirens:
            if siren not in seen_sirens and len(raw_companies) < count:
                seen_sirens.add(siren)
                # Create a minimal search-info stub — will be enriched below
                raw_companies.append({"siren": siren, "nom_entreprise": "", "_from_bodacc": True})
                bodacc_added += 1
        print(f"[Papperclip] BODACC hot SIRENs: +{bodacc_added} (pool {len(raw_companies)})")

    print(f"[Papperclip] Collected {len(raw_companies)} unique companies. Enriching...")

    # ── Phase 3: Enrich all companies ────────────────────────────────
    targets = []
    for idx, company in enumerate(raw_companies, start=1):
        siren = company.get("siren", "")
        nom = company.get("nom_entreprise", "") or siren
        print(f"[Papperclip] Enriching {idx}/{len(raw_companies)}: {nom} ({siren})...")
        try:
            company_info = await get_full_company_info(siren)
            if not company_info:
                continue
            target = build_target(idx=idx, company_info=company_info, search_info=company)
            targets.append(target)
            print(
                f"[Papperclip]   OK: {target['name']} | {target['sector']} "
                f"| score placeholder | {len(target['active_signals'])} signals"
            )
        except Exception as e:
            print(f"[Papperclip]   Error for {siren}: {e}")

    print(f"[Papperclip] Pipeline complete: {len(targets)} targets built.")
    return targets
