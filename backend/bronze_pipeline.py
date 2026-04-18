"""
EdRCF 6.0 — bronze_pipeline.py
Pipeline Bronze / Silver avec DuckDB + MotherDuck.

Architecture :
  Bronze  → DuckDB (MotherDuck) — 16M entités SIRENE brutes (tous secteurs)
  Silver  → DuckDB (MotherDuck) — ~50-80K PME/ETI M&A-éligibles filtrées + scorées
  Gold    → Supabase             — ~5-10K cibles enrichies (existant)

Prérequis :
  pip install duckdb
  Env : MOTHERDUCK_TOKEN=<token>  (depuis app.motherduck.com → Settings → Tokens)

Usage CLI :
  python bronze_pipeline.py setup           → crée les tables sur MotherDuck
  python bronze_pipeline.py load-bronze     → charge les 16M depuis SIRENE CSV.gz
  python bronze_pipeline.py build-silver    → filtre Bronze → Silver (~50-80K)
  python bronze_pipeline.py stats           → stats Bronze + Silver
  python bronze_pipeline.py sync-supabase   → pousse Silver top-N vers sirene_index
  python bronze_pipeline.py full            → setup + load-bronze + build-silver
"""

import asyncio
import io
import os
import re
import sys
import tarfile
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, date

import httpx
from dotenv import load_dotenv

load_dotenv()

# ── Optionnel : duckdb peut ne pas être installé sur certains envs ──────────
try:
    import duckdb
    _DUCKDB_OK = True
except ImportError:
    _DUCKDB_OK = False

# =============================================================================
# Configuration
# =============================================================================

MOTHERDUCK_TOKEN = os.getenv("MOTHERDUCK_TOKEN", "")
MOTHERDUCK_PG_HOST = "pg.eu-central-1-aws.motherduck.com"

# Tracker de progression (accessible via /api/admin/bronze-stats)
_PIPELINE_STATUS: dict = {
    "running": False,
    "step": "idle",
    "rows_loaded": 0,
    "error": None,
    "started_at": None,
    "finished_at": None,
}
DB_NAME          = "edrcf"          # base MotherDuck
BRONZE_TABLE     = "bronze_sirene"  # 16M entités brutes
SILVER_TABLE     = "silver_ma"      # ~50-80K PME/ETI éligibles

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

DATAGOUV_API = "https://www.data.gouv.fr/api/1/datasets/5b7ffc618b4c4169d30727e0/"

# Fallbacks directs — utilisés si l'API data.gouv.fr est indisponible
_BASE_OBJECT = "https://object.files.data.gouv.fr/data-pipeline-open/siren/stock"
SIRENE_UL_PARQUET_FALLBACK   = f"{_BASE_OBJECT}/StockUniteLegale_utf8.parquet"
SIRENE_ETAB_PARQUET_FALLBACK = f"{_BASE_OBJECT}/StockEtablissement_utf8.parquet"


def _fetch_sirene_urls() -> dict:
    """Interroge l'API data.gouv.fr et retourne un dict {keyword: url} pour les fichiers Parquet SIRENE.
    Cherche 'stockuniteleg' (unités légales) et 'stocketabli' (établissements).
    """
    result = {}
    try:
        req = urllib.request.Request(DATAGOUV_API, headers={"User-Agent": "EdRCF/6.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            import json as _json
            data = _json.loads(resp.read())
            for res in data.get("resources", []):
                url   = res.get("url", "")
                title = res.get("title", "").lower()
                if "historique" in title or not url.endswith(".parquet"):
                    continue
                if "stockuniteleg" in title:
                    result["ul"] = url
                    print(f"[BRONZE] URL UnitéLégale : {url}")
                elif ("stocketabli" in title
                      and "lien" not in title
                      and "succession" not in title):
                    result["etab"] = url
                    print(f"[BRONZE] URL Etablissement : {url}")
    except Exception as e:
        print(f"[BRONZE] data.gouv.fr API error: {e} — fallback URLs")
    return result


def get_sirene_urls() -> tuple[str, str]:
    """Retourne (ul_url, etab_url) pour les fichiers Parquet SIRENE.
    ul_url   → StockUniteLegale  (siren, ~29M)
    etab_url → StockEtablissement (siret, ~35M) — uniquement pour extraire le dept du siège
    L'URL etab est toujours hardcodée : l'API data.gouv.fr peut renvoyer
    StockEtablissementLiensSuccession (schéma incompatible) avant le fichier principal.
    """
    urls = _fetch_sirene_urls()
    ul_url   = urls.get("ul", SIRENE_UL_PARQUET_FALLBACK)
    etab_url = SIRENE_ETAB_PARQUET_FALLBACK   # toujours hardcodée — URL confirmée
    return ul_url, etab_url

UPSERT_BATCH = 500   # lignes par appel Supabase

# ── BODACC ───────────────────────────────────────────────────────────────────
BODACC_TABLE = "bronze_bodacc"

# Source primaire : archives tar.gz DILA (sans rate-limit, source officielle)
# Structure réelle du serveur DILA :
#   FluxHistorique/{year}.tar.gz  → archives annuelles 2022-2025 (~100-500 MB)
#   FluxAnneeCourante/BILAN_BXC{year}{NNN}.taz  → flux hebdomadaires de l'année en cours
_DILA_BASE = "https://echanges.dila.gouv.fr/OPENDATA/BODACC"
_DILA_HISTORIQUE = f"{_DILA_BASE}/FluxHistorique"
_DILA_COURANTE   = f"{_DILA_BASE}/FluxAnneeCourante"

# Fallback : OpenDataSoft CSV (pratique pour < 1 an)
_BODACC_ODS_BASE = (
    "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets"
    "/annonces-commerciales/exports/csv"
    "?delimiter=%3B&timezone=UTC"
    "&where=familleavis%20IN%20(%27vente%27%2C%27collective%27)"
)

BODACC_DDL = f"""
CREATE TABLE IF NOT EXISTS {BODACC_TABLE} (
    siren           VARCHAR(9),
    type_annonce    VARCHAR(10),   -- PROCOL | VENTE
    date_parution   DATE,
    denomination    TEXT,
    loaded_at       TIMESTAMP DEFAULT current_timestamp
);
"""

# ── Pappers (data.gouv.fr) ────────────────────────────────────────────────────
PAPPERS_TABLE = "bronze_pappers"

PAPPERS_DDL = f"""
CREATE TABLE IF NOT EXISTS {PAPPERS_TABLE} (
    siren              VARCHAR(9)  NOT NULL,
    denomination       TEXT,
    forme_juridique    TEXT,
    code_naf           VARCHAR(6),
    date_creation      DATE,
    effectif_min       INTEGER,
    effectif_max       INTEGER,
    chiffre_affaires   BIGINT,
    resultat_net       BIGINT,
    code_postal        VARCHAR(5),
    ville              TEXT,
    loaded_at          TIMESTAMP DEFAULT current_timestamp
);
"""

# Pappers publie leur base sur data.gouv.fr — dataset ID stable
_PAPPERS_DATAGOUV_SEARCH = (
    "https://www.data.gouv.fr/api/1/datasets/?q=pappers+entreprises&page_size=5"
)

# =============================================================================
# Codes NAF et filtres (répliqués de sirene_bulk.py)
# =============================================================================

SIRENE_NAF_CODES: set[str] = {
    "6622Z","6629Z","6430Z","6630Z","6420Z","6419Z",
    "4941A","4941B","5210B","5229A",
    "4120A","4321A","4322A","4399C","4110A",
    "7022Z","6920Z","6910Z","7810Z","8010Z","8121Z","8110Z",
    "3250A","8610Z","4773Z","2120Z","8690B",
    "2899B","2611Z","2932Z","2452Z","2512Z","2591Z",
    "6201Z","6202A","5829C","6312Z",
    "1089Z","1102A","1071A","1011Z",
    "3511Z","7112B","3831Z","3700Z",
    "4669Z","4663Z","4639B","4646Z",
    "5530Z","5510Z","5610A",
    "4110B","6832A",
    "8559B","8542Z",
    "4511Z","4520A",
    "7311Z","5814Z",
    "3030Z","3040Z",
}

ELIGIBLE_EFFECTIF: set[str] = {"11","12","21","22","31","32","41","42","51","52","53"}

ELIGIBLE_CJ: set[str] = {
    "5498","5499","5710","5720",
    "5410","5422",
    "5599","5505","5510","5699",
    "5307",
}

# =============================================================================
# Connexion DuckDB / MotherDuck
# =============================================================================

def _ensure_database() -> None:
    """Crée la base MotherDuck 'edrcf' si elle n'existe pas encore."""
    if not _DUCKDB_OK or not MOTHERDUCK_TOKEN:
        return
    try:
        # Utilise la variable d'env motherduck_token (lue automatiquement par DuckDB)
        os.environ["motherduck_token"] = MOTHERDUCK_TOKEN
        con = duckdb.connect("md:")
        con.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        con.close()
        print(f"[DuckDB] Base '{DB_NAME}' prête sur MotherDuck.")
    except Exception as e:
        print(f"[DuckDB] _ensure_database warning: {e}")


def _get_connection(local_fallback: bool = False):
    """Retourne une connexion DuckDB.
    - Si MOTHERDUCK_TOKEN défini → connexion MotherDuck cloud via env var
    - Sinon → fichier local edrcf.duckdb (développement)
    """
    if not _DUCKDB_OK:
        raise RuntimeError("duckdb non installé. Exécuter : pip install duckdb")

    if MOTHERDUCK_TOKEN and not local_fallback:
        # DuckDB lit motherduck_token depuis l'environnement — évite les pb de JWT en query string
        os.environ["motherduck_token"] = MOTHERDUCK_TOKEN
        _ensure_database()
        conn_str = f"md:{DB_NAME}"
        print(f"[DuckDB] Connexion MotherDuck : md:{DB_NAME}")
    else:
        conn_str = "edrcf.duckdb"
        print(f"[DuckDB] Connexion locale : edrcf.duckdb")

    return duckdb.connect(conn_str)


# =============================================================================
# SETUP — création des tables
# =============================================================================

BRONZE_DDL = f"""
CREATE TABLE IF NOT EXISTS {BRONZE_TABLE} (
    siren                  VARCHAR(9)  NOT NULL,
    denomination           TEXT,
    naf                    VARCHAR(6),
    dept                   VARCHAR(3),
    effectif_tranche       VARCHAR(4),
    date_creation          DATE,
    categorie_juridique    VARCHAR(6),
    categorie_entreprise   VARCHAR(10),
    etat_administratif     VARCHAR(1),   -- A = active, F = fermée, C = cessée
    loaded_at              TIMESTAMP DEFAULT current_timestamp
);
"""

SILVER_DDL = f"""
CREATE TABLE IF NOT EXISTS {SILVER_TABLE} (
    siren                  VARCHAR(9)  PRIMARY KEY,
    denomination           TEXT,
    naf                    VARCHAR(6),
    dept                   VARCHAR(3),
    effectif_tranche       VARCHAR(4),
    date_creation          DATE,
    categorie_juridique    VARCHAR(6),
    categorie_entreprise   VARCHAR(10),
    ma_score               SMALLINT    DEFAULT 0,
    bodacc_recent          BOOLEAN     DEFAULT false,
    -- Adresse (SIRENE StockEtablissement)
    adresse                TEXT,
    code_postal            VARCHAR(5),
    ville                  TEXT,
    -- Contact (recherche-entreprises.api.gouv.fr)
    site_web               TEXT,
    telephone              VARCHAR(20),
    linkedin_url           TEXT,
    email_domaine          TEXT,
    -- Dirigeant (INPI RNE)
    nom_dirigeant          TEXT,
    qualite_dirigeant      TEXT,
    annee_naissance        SMALLINT,
    -- Financier (INPI SFTP — à venir)
    chiffre_affaires       BIGINT,
    resultat_net           BIGINT,
    -- Suivi enrichissement
    enriched               BOOLEAN     DEFAULT false,
    enriched_at            TIMESTAMP,
    silver_at              TIMESTAMP   DEFAULT current_timestamp
);
"""


def setup_tables() -> None:
    """Crée les tables Bronze, Silver, BODACC et Pappers sur MotherDuck (idempotent)."""
    con = _get_connection()
    print("[DuckDB] Création des tables Bronze + Silver + BODACC + Pappers…")
    con.execute(BRONZE_DDL)
    con.execute(SILVER_DDL)
    con.execute(BODACC_DDL)
    con.execute(PAPPERS_DDL)
    # Migrations : colonnes ajoutées après création initiale
    _migrate_cols = [
        ("adresse", "TEXT"), ("code_postal", "VARCHAR(5)"), ("ville", "TEXT"),
        ("nom_dirigeant", "TEXT"), ("qualite_dirigeant", "TEXT"),
        ("annee_naissance", "SMALLINT"), ("chiffre_affaires", "BIGINT"),
        ("resultat_net", "BIGINT"),
    ]
    for col, typ in _migrate_cols:
        try:
            con.execute(f"ALTER TABLE {SILVER_TABLE} ADD COLUMN IF NOT EXISTS {col} {typ}")
        except Exception:
            pass
    # Index Silver
    con.execute(f"CREATE INDEX IF NOT EXISTS idx_silver_score ON {SILVER_TABLE} (ma_score DESC)")
    con.execute(f"CREATE INDEX IF NOT EXISTS idx_silver_naf   ON {SILVER_TABLE} (naf)")
    con.execute(f"CREATE INDEX IF NOT EXISTS idx_silver_dept  ON {SILVER_TABLE} (dept)")
    # Index BODACC
    con.execute(f"CREATE INDEX IF NOT EXISTS idx_bodacc_siren ON {BODACC_TABLE} (siren)")
    con.execute(f"CREATE INDEX IF NOT EXISTS idx_bodacc_date  ON {BODACC_TABLE} (date_parution)")
    # Index Pappers
    con.execute(f"CREATE INDEX IF NOT EXISTS idx_pappers_siren ON {PAPPERS_TABLE} (siren)")
    con.close()
    print("[DuckDB] ✅ Tables prêtes.")


# =============================================================================
# BRONZE — chargement des 16M entités SIRENE
# =============================================================================

def load_bronze(ul_url: str | None = None) -> int:
    """
    Charge toutes les entités SIRENE (StockUniteLegale) dans Bronze.
    dept = NULL à ce stade — sera renseigné dans build_silver() sur les ~87K
    lignes filtrées (JOIN avec StockEtablissement sur un sous-ensemble, bien plus rapide).
    Retourne le nombre de lignes insérées.
    """
    global _PIPELINE_STATUS

    resolved_ul, _ = get_sirene_urls()
    ul_url = ul_url or resolved_ul

    con = _get_connection()
    _PIPELINE_STATUS.update({"step": "bronze_load", "rows_loaded": 0, "error": None})

    print(f"[BRONZE] Vidage table existante…")
    con.execute(f"DELETE FROM {BRONZE_TABLE}")

    print(f"[BRONZE] UL : {ul_url}")
    t0 = time.time()

    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"""
        INSERT INTO {BRONZE_TABLE}
            (siren, denomination, naf, dept, effectif_tranche,
             date_creation, categorie_juridique, categorie_entreprise,
             etat_administratif)
        SELECT
            siren                                                           AS siren,
            denominationUniteLegale                                         AS denomination,
            REPLACE(COALESCE(activitePrincipaleUniteLegale,''), '.', '')    AS naf,
            NULL                                                            AS dept,
            trancheEffectifsUniteLegale                                     AS effectif_tranche,
            TRY_CAST(dateCreationUniteLegale AS DATE)                       AS date_creation,
            categorieJuridiqueUniteLegale                                   AS categorie_juridique,
            categorieEntreprise                                             AS categorie_entreprise,
            etatAdministratifUniteLegale                                    AS etat_administratif
        FROM read_parquet('{ul_url}')
    """)

    count = con.execute(f"SELECT COUNT(*) FROM {BRONZE_TABLE}").fetchone()[0]
    elapsed = time.time() - t0
    _PIPELINE_STATUS["rows_loaded"] = count
    con.close()
    print(f"[BRONZE] ✅ {count:,} entités en {elapsed/60:.1f} min.")
    return count


# =============================================================================
# SILVER — filtrage M&A + scoring
# =============================================================================

def _naf_list_sql() -> str:
    """Génère la liste SQL des codes NAF cibles."""
    return ", ".join(f"'{c}'" for c in sorted(SIRENE_NAF_CODES))


def _effectif_list_sql() -> str:
    return ", ".join(f"'{e}'" for e in sorted(ELIGIBLE_EFFECTIF))


def _cj_list_sql() -> str:
    return ", ".join(f"'{c}'" for c in sorted(ELIGIBLE_CJ))


def _high_ma_naf_sql() -> str:
    HIGH = {"6622Z","6629Z","6420Z","6430Z","7022Z","6920Z","4941A","4941B","4120A","6201Z","6202A"}
    return ", ".join(f"'{c}'" for c in sorted(HIGH))


def build_silver(etab_url: str | None = None) -> int:
    """
    Filtre Bronze → Silver avec les critères M&A et calcule le score.
    Enrichit dept via JOIN StockEtablissement sur les ~87K lignes éligibles
    (bien plus rapide qu'un JOIN sur les 29M lignes Bronze).
    Retourne le nombre de lignes dans Silver.
    """
    _, resolved_etab = get_sirene_urls()
    etab_url = etab_url or resolved_etab

    con = _get_connection()
    print("[SILVER] Construction de la couche Silver…")
    t0 = time.time()

    con.execute(f"DELETE FROM {SILVER_TABLE}")
    con.execute("INSTALL httpfs; LOAD httpfs;")

    con.execute(f"""
        INSERT INTO {SILVER_TABLE}
            (siren, denomination, naf, dept, effectif_tranche,
             date_creation, categorie_juridique, categorie_entreprise,
             adresse, code_postal, ville,
             ma_score)
        SELECT
            b.siren,
            b.denomination,
            b.naf,
            -- dept + adresse depuis StockEtablissement (même parquet, 0 coût supplémentaire)
            LEFT(COALESCE(e.codeCommuneEtablissement, ''), 2)   AS dept,
            b.effectif_tranche,
            b.date_creation,
            b.categorie_juridique,
            b.categorie_entreprise,
            -- Adresse complète reconstituée
            TRIM(
                COALESCE(e.numeroVoieEtablissement, '') || ' ' ||
                COALESCE(e.typeVoieEtablissement,   '') || ' ' ||
                COALESCE(e.libelleVoieEtablissement,'')
            )                                                    AS adresse,
            e.codePostalEtablissement                            AS code_postal,
            e.libelleCommuneEtablissement                        AS ville,
            -- Score M&A 0-100
            LEAST(100,
                CASE b.effectif_tranche
                    WHEN '11' THEN 15  WHEN '12' THEN 20
                    WHEN '21' THEN 25  WHEN '22' THEN 25
                    WHEN '31' THEN 20  WHEN '32' THEN 18
                    WHEN '41' THEN 12  WHEN '42' THEN 8
                    WHEN '51' THEN 5   WHEN '52' THEN 3  WHEN '53' THEN 2
                    ELSE 0
                END
                +
                CASE
                    WHEN b.date_creation IS NULL                               THEN 0
                    WHEN YEAR(CURRENT_DATE) - YEAR(b.date_creation) BETWEEN 3  AND 4  THEN 8
                    WHEN YEAR(CURRENT_DATE) - YEAR(b.date_creation) BETWEEN 5  AND 9  THEN 15
                    WHEN YEAR(CURRENT_DATE) - YEAR(b.date_creation) BETWEEN 10 AND 25 THEN 20
                    WHEN YEAR(CURRENT_DATE) - YEAR(b.date_creation) > 25              THEN 12
                    ELSE 0
                END
                +
                CASE b.categorie_juridique
                    WHEN '5498' THEN 15  WHEN '5499' THEN 15
                    WHEN '5710' THEN 15  WHEN '5720' THEN 15
                    WHEN '5410' THEN 14  WHEN '5422' THEN 14
                    WHEN '5599' THEN 12  WHEN '5505' THEN 12
                    WHEN '5510' THEN 12  WHEN '5699' THEN 12
                    WHEN '5307' THEN 8
                    ELSE 0
                END
                +
                CASE b.categorie_entreprise
                    WHEN 'ETI' THEN 15
                    WHEN 'PME' THEN 10
                    ELSE 0
                END
                +
                CASE WHEN b.naf IN ({_high_ma_naf_sql()}) THEN 5 ELSE 0 END
            ) AS ma_score
        FROM {BRONZE_TABLE} AS b
        LEFT JOIN (
            SELECT siren,
                   codeCommuneEtablissement,
                   numeroVoieEtablissement,
                   typeVoieEtablissement,
                   libelleVoieEtablissement,
                   codePostalEtablissement,
                   libelleCommuneEtablissement
            FROM read_parquet('{etab_url}')
            WHERE etablissementSiege = 'true'
        ) AS e ON b.siren = e.siren
        WHERE b.etat_administratif = 'A'
          AND b.categorie_entreprise IN ('PME', 'ETI')
          AND b.naf IN ({_naf_list_sql()})
          AND b.effectif_tranche IN ({_effectif_list_sql()})
    """)

    count = con.execute(f"SELECT COUNT(*) FROM {SILVER_TABLE}").fetchone()[0]
    elapsed = time.time() - t0
    con.close()
    print(f"[SILVER] ✅ {count:,} PME/ETI M&A-éligibles en {elapsed:.1f}s.")
    return count


# =============================================================================
# BODACC — chargement via DILA (source officielle) + fallback ODS
# =============================================================================

def _parse_bodacc_xml(xml_bytes: bytes, annonce_type: str) -> list[tuple]:
    """
    Parse un fichier XML BODACC DILA et retourne [(siren, annonce_type, date, denom)].
    Gère BODACC-A (vente) et BODACC-B (procol) avec extraction SIREN robuste.
    """
    rows: list[tuple] = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return rows

    for avis in root.iter("avis"):
        type_elem = avis.find("typeAnnonce")
        if type_elem is None:
            continue

        # Filtre selon le type demandé
        if annonce_type == "VENTE" and type_elem.find("vente") is None:
            continue
        if annonce_type == "PROCOL":
            # BODACC-B regroupe plusieurs jugements de procédures collectives
            procol_tags = {
                "jugementPrononceOuvertureSauvegarde",
                "jugementPrononceOuvertureRedressementJudiciaire",
                "jugementPrononceRedressementJudiciaire",
                "jugementDeclarantFaillitePersonnelle",
                "jugementOuvrantLiquidationJudiciaire",
                "jugementArreteOuPrononceLiquidationJudiciaire",
                "proce",
            }
            if not any(type_elem.find(t) is not None for t in procol_tags):
                continue

        # Date de parution (format YYYYMMDD ou YYYY-MM-DD)
        date_obj = None
        date_str = (avis.findtext("dateParution") or "").strip().replace("-", "")
        if len(date_str) == 8 and date_str.isdigit():
            try:
                date_obj = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
            except ValueError:
                pass

        # SIREN — cherche <numeroIdentification> (9 chiffres exactement)
        siren = None
        for elem in avis.iter("numeroIdentification"):
            val = (elem.text or "").strip()
            if len(val) == 9 and val.isdigit():
                siren = val
                break

        if not siren:
            # Fallback regex sur le texte brut de l'avis
            avis_text = ET.tostring(avis, encoding="unicode")
            m = re.search(r'\b(\d{9})\b', avis_text)
            if m:
                siren = m.group(1)

        # Dénomination sociale
        denom = ""
        for tag in ("denominationSociale", "nom", "raisonSociale", "nomEntreprise"):
            elem = avis.find(f".//{tag}")
            if elem is not None and elem.text:
                denom = elem.text.strip()[:200]
                break

        if siren:
            rows.append((siren, annonce_type, date_obj, denom))

    return rows


def _stream_download(url: str, dest: str) -> bool:
    """Télécharge url → dest en streaming. Retourne True si succès."""
    try:
        downloaded = 0
        with httpx.Client(timeout=None, follow_redirects=True,
                          headers={"User-Agent": "EdRCF/6.0"}) as client:
            with client.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(dest, "wb") as fp:
                    for chunk in resp.iter_bytes(131_072):
                        fp.write(chunk)
                        downloaded += len(chunk)
                        if downloaded % 50_000_000 < 131_072:
                            print(f"[DILA]   {downloaded/1e6:.0f} MB…")
        print(f"[DILA] Téléchargé {os.path.getsize(dest)/1e6:.1f} MB → {dest}")
        return True
    except Exception as e:
        print(f"[DILA] Échec {url}: {type(e).__name__}: {e}")
        return False


def _dila_list_courante() -> list[str]:
    """Retourne les URLs des flux hebdomadaires de l'année courante (FluxAnneeCourante/)."""
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as c:
            r = c.get(_DILA_COURANTE + "/")
            r.raise_for_status()
        import re as _re
        links = _re.findall(r'href="(BILAN_BXC[^"]+\.taz)"', r.text)
        return [f"{_DILA_COURANTE}/{f}" for f in sorted(links)]
    except Exception as e:
        print(f"[DILA] Erreur listing FluxAnneeCourante: {e}")
        return []


def _insert_bodacc_batch(rows: list[tuple]) -> int:
    """Insert un batch dans bronze_bodacc. Retourne le nb de lignes insérées."""
    if not rows:
        return 0
    con = _get_connection()
    try:
        con.executemany(
            f"INSERT INTO {BODACC_TABLE} (siren, type_annonce, date_parution, denomination)"
            f" VALUES (?, ?, ?, ?)",
            rows,
        )
        return len(rows)
    finally:
        con.close()


def _parse_tar_bodacc(tmp_path: str) -> list[tuple]:
    """
    Extrait les lignes BODACC d'un archive .tar.gz / .taz.
    Gère les archives imbriquées : si l'archive contient d'autres .taz/.tar.gz,
    les extrait récursivement (ex: FluxHistorique/2025.tar.gz → semaines .taz → XML).
    """
    rows: list[tuple] = []
    try:
        with tarfile.open(tmp_path, "r:*") as tar:
            for member in tar.getmembers():
                name = member.name.lower()
                f = tar.extractfile(member)
                if not f:
                    continue
                if name.endswith(".xml"):
                    # Détermine le type depuis le nom du fichier
                    annonce_type = "PROCOL" if "_b_" in name or "bodacc-b" in name else "VENTE"
                    rows.extend(_parse_bodacc_xml(f.read(), annonce_type))
                elif name.endswith((".taz", ".tar.gz", ".tgz")):
                    # Archive imbriquée (ex: semaine dans l'archive annuelle)
                    inner_tmp = f"/tmp/bodacc_inner_{os.path.basename(name)}"
                    try:
                        with open(inner_tmp, "wb") as out:
                            out.write(f.read())
                        rows.extend(_parse_tar_bodacc(inner_tmp))
                    except Exception as e2:
                        print(f"[DILA] Erreur archive imbriquée {name}: {e2}")
                    finally:
                        try:
                            os.unlink(inner_tmp)
                        except OSError:
                            pass
    except Exception as e:
        print(f"[DILA] Erreur parse {tmp_path}: {e}")
    return rows


def load_bodacc_dila(since: str = "2023-01-01") -> int:
    """
    Charge les annonces BODACC depuis les archives DILA (sans rate-limit).
    URLs réelles :
      FluxHistorique/{year}.tar.gz  → années 2022-2025
      FluxAnneeCourante/BILAN_BXC{year}{NNN}.taz  → semaines de l'année en cours
    Insert par archive pour limiter la mémoire.
    """
    since_year = int(since.split("-")[0])
    current_year = datetime.now().year

    total_inserted = 0

    # ── Années complètes depuis FluxHistorique ──────────────────────────────
    for year in range(since_year, current_year):
        url = f"{_DILA_HISTORIQUE}/{year}.tar.gz"
        tmp = f"/tmp/bodacc_{year}.tar.gz"
        print(f"[DILA] Téléchargement {url} …")
        if not _stream_download(url, tmp):
            print(f"[DILA] Archive {year} introuvable — ignorée.")
            continue
        rows = _parse_tar_bodacc(tmp)
        try:
            os.unlink(tmp)
        except OSError:
            pass
        inserted = _insert_bodacc_batch(rows)
        total_inserted += inserted
        print(f"[DILA] {year}: {inserted:,} lignes → cumul {total_inserted:,}")

    # ── Année courante depuis FluxAnneeCourante (flux hebdomadaires) ─────────
    weekly_urls = _dila_list_courante()
    print(f"[DILA] FluxAnneeCourante: {len(weekly_urls)} fichiers hebdomadaires")
    for url in weekly_urls:
        fname = os.path.basename(url)
        tmp = f"/tmp/{fname}"
        if not _stream_download(url, tmp):
            continue
        rows = _parse_tar_bodacc(tmp)
        try:
            os.unlink(tmp)
        except OSError:
            pass
        inserted = _insert_bodacc_batch(rows)
        total_inserted += inserted

    if total_inserted == 0:
        print("[DILA] Aucune donnée extraite — table existante préservée.")
    else:
        # Purge des anciennes données SEULEMENT si le rechargement a réussi
        con = _get_connection()
        try:
            existing = con.execute(f"SELECT COUNT(*) FROM {BODACC_TABLE}").fetchone()[0]
            if existing > total_inserted:
                con.execute(
                    f"DELETE FROM {BODACC_TABLE} WHERE loaded_at < (SELECT MAX(loaded_at) FROM {BODACC_TABLE})"
                )
            for t, n in con.execute(
                f"SELECT type_annonce, COUNT(*) FROM {BODACC_TABLE} GROUP BY 1"
            ).fetchall():
                print(f"[DILA]   {t}: {n:,}")
            print(f"[DILA] Total {total_inserted:,} annonces chargées.")
        finally:
            con.close()
    return total_inserted


_ODS_JSON_BASE = (
    "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets"
    "/annonces-commerciales/records"
)
_ODS_PAGE_SIZE = 100   # max autorisé par l'API ODS v2.1
_ODS_COMMIT_EVERY = 1_000  # lignes avant commit MotherDuck


async def _load_bodacc_ods(since: str = "2023-01-01") -> int:
    """Chargement BODACC via API JSON paginée ODS — séquentiel, robuste."""
    import re as _re

    where = f"familleavis IN ('vente','collective') AND dateparution >= '{since}'"
    params_base = {
        "limit": _ODS_PAGE_SIZE,
        "where": where,
        "select": "registre,familleavis,dateparution,commercant",
        "timezone": "UTC",
    }

    async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                  headers={"User-Agent": "EdRCF/6.0"}) as client:
        r = await client.get(_ODS_JSON_BASE, params={**params_base, "limit": 1})
        r.raise_for_status()
        total_count = r.json().get("total_count", 0)

    print(f"[BODACC ODS] {total_count:,} annonces à charger depuis {since}…")
    if total_count == 0:
        return 0

    total_inserted = 0
    buffer: list[tuple] = []

    def _flush(rows: list[tuple]) -> int:
        if not rows:
            return 0
        con = _get_connection()
        try:
            placeholders = ",".join(["(?,?,?,?)"] * len(rows))
            flat = [v for row in rows for v in row]
            con.execute(
                f"INSERT INTO {BODACC_TABLE} (siren, type_annonce, date_parution, denomination)"
                f" VALUES {placeholders}",
                flat,
            )
            return len(rows)
        except Exception as e:
            print(f"[BODACC ODS] Flush error: {e}")
            return 0
        finally:
            con.close()

    async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                  headers={"User-Agent": "EdRCF/6.0"}) as client:
        offset = 0
        page_num = 0
        while offset < total_count:
            for attempt in range(3):
                try:
                    r = await client.get(_ODS_JSON_BASE,
                                         params={**params_base, "offset": offset})
                    r.raise_for_status()
                    break
                except Exception as e:
                    if attempt == 2:
                        print(f"[BODACC ODS] Page {page_num} échouée: {e}")
                        offset += _ODS_PAGE_SIZE
                        continue
                    await asyncio.sleep(2 ** attempt)

            for rec in r.json().get("results", []):
                registre = rec.get("registre") or []
                siren = next(
                    (s for s in registre if _re.fullmatch(r"\d{9}", s)), None
                )
                if not siren:
                    continue
                type_av = "VENTE" if rec.get("familleavis") == "vente" else "PROCOL"
                buffer.append((siren, type_av, rec.get("dateparution"), (rec.get("commercant") or "")[:200]))

            offset += _ODS_PAGE_SIZE
            page_num += 1

            if len(buffer) >= _ODS_COMMIT_EVERY:
                n = _flush(buffer)
                total_inserted += n
                buffer.clear()
                print(f"[BODACC ODS] {total_inserted:,} / ~{total_count:,} insérés…")

    if buffer:
        total_inserted += _flush(buffer)

    print(f"[BODACC ODS] ✅ {total_inserted:,} annonces chargées (≥{since}).")
    return total_inserted


def load_bodacc(since: str = "2023-01-01") -> int:
    """
    Charge les annonces BODACC : essaie DILA (archives annuelles tar.gz) en premier,
    puis fallback OpenDataSoft JSON paginé si DILA échoue.
    """
    print(f"[BODACC] Chargement depuis DILA (primaire) puis ODS JSON (fallback)…")
    total = load_bodacc_dila(since=since)
    if total == 0:
        print("[BODACC] DILA n'a rien retourné — fallback OpenDataSoft JSON paginé…")
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(1) as pool:
                    future = pool.submit(asyncio.run, _load_bodacc_ods(since))
                    total = future.result()
            else:
                total = loop.run_until_complete(_load_bodacc_ods(since))
        except Exception as e:
            print(f"[BODACC ODS] Erreur: {e}")
    return total


def flag_bodacc_silver(months: int = 24) -> int:
    """
    Met à jour bodacc_recent=true dans Silver pour les SIRENs
    ayant une annonce BODACC dans les `months` derniers mois.
    Ajoute +15 au ma_score (capped à 100) pour les signaux VENTE/PROCOL.
    Retourne le nombre de lignes mises à jour.
    """
    con = _get_connection()
    print(f"[BODACC] Flagging Silver (bodacc_recent) sur {months} mois…")

    con.execute(f"""
        UPDATE {SILVER_TABLE}
        SET bodacc_recent = true,
            ma_score      = LEAST(100, ma_score + 15)
        WHERE siren IN (
            SELECT DISTINCT siren
            FROM {BODACC_TABLE}
            WHERE date_parution >= CURRENT_DATE - INTERVAL ('{months} months')
              AND type_annonce IN ('VENTE', 'PROCOL')
              AND siren IS NOT NULL
        )
    """)

    updated = con.execute(
        f"SELECT COUNT(*) FROM {SILVER_TABLE} WHERE bodacc_recent = true"
    ).fetchone()[0]
    con.close()
    print(f"[BODACC] ✅ {updated:,} entreprises Silver flaggées bodacc_recent=true.")
    return updated


# =============================================================================
# PAPPERS — data.gouv.fr (base Pappers open data)
# =============================================================================

def load_pappers_bronze() -> int:
    """
    STATUT : NON DISPONIBLE — le pseudo-dataset "Pappers" sur data.gouv.fr est un
    micro-extrait <1 Mo figé en juillet 2021 publié par un portail Pays Basque, sans rapport
    avec la base Pappers réelle. L'API Pappers interdit explicitement la redistribution dans un
    SaaS tiers (CGU §usage commercial) sauf contrat "Redistribution" négocié.

    ALTERNATIVES SOUVERAINES À IMPLÉMENTER :
    - INPI RNE SFTP : comptes annuels + dirigeants + actes pour 10 M entreprises
      → inscription gratuite sur data.inpi.fr (délai ~1-4 semaines)
    - Annuaire Entreprises Etalab (github.com/annuaire-entreprises-data-gouv-fr)
      → licence MIT, forkable, maintenu par la DINUM

    Retourne 0 jusqu'à intégration d'une vraie source financière.
    """
    print("[PAPPERS] Dataset Pappers data.gouv.fr indisponible (cf. audit juridique).")
    print("[PAPPERS] Pour les données financières, utiliser INPI RNE SFTP après inscription.")
    return 0


def enrich_silver_pappers() -> int:
    """Sera opérationnel quand bronze_pappers sera alimenté (INPI SFTP ou source souveraine)."""
    con = _get_connection()
    try:
        count = con.execute(f"SELECT COUNT(*) FROM {PAPPERS_TABLE}").fetchone()[0]
    except Exception:
        count = 0
    finally:
        con.close()
    if count == 0:
        print("[PAPPERS] bronze_pappers vide — enrich ignoré.")
        return 0
    # Bonus financiers (actif une fois INPI SFTP chargé)
    con = _get_connection()
    try:
        con.execute(f"""
            UPDATE {SILVER_TABLE} SET ma_score = LEAST(100, ma_score + 8)
            WHERE siren IN (SELECT siren FROM {PAPPERS_TABLE} WHERE chiffre_affaires >= 5000000)
        """)
        con.execute(f"""
            UPDATE {SILVER_TABLE} SET ma_score = LEAST(100, ma_score + 5)
            WHERE siren IN (SELECT siren FROM {PAPPERS_TABLE}
                WHERE chiffre_affaires >= 1000000 AND chiffre_affaires < 5000000)
        """)
        con.execute(f"""
            UPDATE {SILVER_TABLE} SET ma_score = LEAST(100, ma_score + 5)
            WHERE siren IN (SELECT siren FROM {PAPPERS_TABLE} WHERE resultat_net > 0)
        """)
        updated = con.execute(f"""
            SELECT COUNT(*) FROM {SILVER_TABLE}
            WHERE siren IN (SELECT DISTINCT siren FROM {PAPPERS_TABLE})
        """).fetchone()[0]
        print(f"[PAPPERS] {updated:,} entreprises Silver enrichies.")
        return updated
    except Exception as e:
        print(f"[PAPPERS] Erreur enrich_silver_pappers: {e}")
        return 0
    finally:
        con.close()


# =============================================================================
# SYNC → Supabase (sirene_index)
# =============================================================================

async def _get_supabase_columns(client: httpx.AsyncClient, headers: dict) -> set:
    """Discovers existing columns in sirene_index by fetching one row."""
    try:
        r = await client.get(
            f"{SUPABASE_URL}/rest/v1/sirene_index",
            params={"limit": "1"},
            headers={**headers, "Prefer": ""},
        )
        if r.status_code == 200:
            data = r.json()
            if data:
                return set(data[0].keys())
    except Exception:
        pass
    return set()


async def sync_silver_to_supabase(top_n: int = 5000, priority: str = "score") -> int:
    """
    Pousse les top_n entreprises Silver vers Supabase sirene_index.
    priority = 'score'   → tri par ma_score DESC
    priority = 'bodacc'  → bodacc_recent DESC, ma_score DESC
    Auto-détecte les colonnes existantes pour résister aux migrations incomplètes.
    Retourne le nombre de lignes upsertées.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[SYNC] Supabase non configuré — sync ignorée.")
        return 0

    con = _get_connection()

    order = "bodacc_recent DESC, ma_score DESC" if priority == "bodacc" else "ma_score DESC"

    # All columns we want to send — subset will be filtered by what exists in Supabase
    all_cols = [
        "siren", "denomination", "naf", "dept", "effectif_tranche", "date_creation",
        "categorie_juridique", "categorie_entreprise", "ma_score_estimate",
        "bodacc_recent", "enriched",
        "adresse", "code_postal", "ville",
        "site_web", "telephone", "linkedin_url", "email_domaine",
        "nom_dirigeant", "qualite_dirigeant", "annee_naissance",
        "chiffre_affaires", "resultat_net",
    ]

    # Silver columns (some aliased differently)
    silver_select = """
        siren, denomination, naf, dept, effectif_tranche,
        date_creation::TEXT AS date_creation,
        categorie_juridique, categorie_entreprise,
        ma_score AS ma_score_estimate,
        bodacc_recent, enriched,
        adresse, code_postal, ville,
        site_web, telephone, linkedin_url, email_domaine,
        nom_dirigeant, qualite_dirigeant, annee_naissance,
        chiffre_affaires, resultat_net
    """

    # Gracefully handle missing columns in Silver (e.g. not yet migrated)
    try:
        rows_df = con.execute(f"""
            SELECT {silver_select}
            FROM {SILVER_TABLE}
            ORDER BY {order}
            LIMIT {top_n}
        """).fetchall()
    except Exception as e:
        print(f"[SYNC] Erreur lecture Silver (colonnes manquantes ?) : {e}")
        # Fallback: only send base columns
        rows_df = con.execute(f"""
            SELECT siren, denomination, naf, dept, effectif_tranche,
                   date_creation::TEXT AS date_creation,
                   categorie_juridique, categorie_entreprise,
                   ma_score AS ma_score_estimate,
                   bodacc_recent, enriched
            FROM {SILVER_TABLE}
            ORDER BY {order}
            LIMIT {top_n}
        """).fetchall()
        all_cols = ["siren","denomination","naf","dept","effectif_tranche","date_creation",
                    "categorie_juridique","categorie_entreprise","ma_score_estimate",
                    "bodacc_recent","enriched"]

    records = [dict(zip(all_cols, r)) for r in rows_df]
    con.close()

    headers = {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "resolution=merge-duplicates",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        # Discover which columns actually exist in Supabase
        existing_cols = await _get_supabase_columns(client, headers)
        if existing_cols:
            # Filter records to only include known columns
            missing = set(all_cols) - existing_cols
            if missing:
                print(f"[SYNC] Colonnes absentes de sirene_index (migration requise) : {sorted(missing)}")
                records = [{k: v for k, v in rec.items() if k in existing_cols} for rec in records]

        print(f"[SYNC] Envoi de {len(records)} lignes vers Supabase sirene_index…")
        total = 0
        for i in range(0, len(records), UPSERT_BATCH):
            batch = records[i : i + UPSERT_BATCH]
            r = await client.post(
                f"{SUPABASE_URL}/rest/v1/sirene_index",
                json=batch,
                headers=headers,
            )
            if r.status_code in (200, 201):
                total += len(batch)
            else:
                print(f"  [SYNC] Erreur batch {i//UPSERT_BATCH}: HTTP {r.status_code} — {r.text[:200]}")

    print(f"[SYNC] {total} lignes synchronisées vers Supabase.")
    return total


# =============================================================================
# STATS
# =============================================================================

def print_stats() -> None:
    """Affiche les statistiques Bronze + Silver."""
    con = _get_connection()

    try:
        bronze_count = con.execute(f"SELECT COUNT(*) FROM {BRONZE_TABLE}").fetchone()[0]
        bronze_active = con.execute(
            f"SELECT COUNT(*) FROM {BRONZE_TABLE} WHERE etat_administratif = 'A'"
        ).fetchone()[0]
        print(f"\n{'='*50}")
        print(f"  BRONZE — {BRONZE_TABLE}")
        print(f"  Total entités     : {bronze_count:>10,}")
        print(f"  Entités actives   : {bronze_active:>10,}")
    except Exception:
        print("[STATS] Table Bronze vide ou inexistante.")

    try:
        silver_count = con.execute(f"SELECT COUNT(*) FROM {SILVER_TABLE}").fetchone()[0]
        enriched = con.execute(
            f"SELECT COUNT(*) FROM {SILVER_TABLE} WHERE enriched = true"
        ).fetchone()[0]
        avg_score = con.execute(
            f"SELECT ROUND(AVG(ma_score)) FROM {SILVER_TABLE}"
        ).fetchone()[0]
        top_nafs = con.execute(f"""
            SELECT naf, COUNT(*) AS n
            FROM {SILVER_TABLE}
            GROUP BY naf ORDER BY n DESC LIMIT 5
        """).fetchall()
        print(f"\n  SILVER — {SILVER_TABLE}")
        print(f"  PME/ETI éligibles : {silver_count:>10,}")
        print(f"  Enrichies (Gold)  : {enriched:>10,}")
        print(f"  Score moyen       : {avg_score:>10}")
        print(f"  Top 5 NAF         :")
        for naf, n in top_nafs:
            print(f"    {naf} : {n:,}")
        print(f"{'='*50}\n")
    except Exception:
        print("[STATS] Table Silver vide ou inexistante.")

    con.close()


# =============================================================================
# Endpoints FastAPI (importés dans main.py)
# =============================================================================

def _pg_stats() -> dict | None:
    """Connexion stats via MotherDuck Postgres endpoint (bypass JWT DuckDB)."""
    if not MOTHERDUCK_TOKEN:
        return None
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=MOTHERDUCK_PG_HOST, port=5432, user="postgres",
            password=MOTHERDUCK_TOKEN, dbname=DB_NAME, sslmode="require",
            connect_timeout=15,
        )
        cur = conn.cursor()
        def q(sql):
            cur.execute(sql); return cur.fetchone()[0]
        bronze   = q(f"SELECT COUNT(*) FROM {BRONZE_TABLE}")
        silver   = q(f"SELECT COUNT(*) FROM {SILVER_TABLE}")
        enriched = q(f"SELECT COUNT(*) FROM {SILVER_TABLE} WHERE enriched = true")
        avg_score = q(f"SELECT ROUND(AVG(ma_score)::numeric, 1) FROM {SILVER_TABLE}")
        bodacc_total = bodacc_flagged = pappers_total = 0
        try:
            bodacc_total  = q(f"SELECT COUNT(*) FROM {BODACC_TABLE}")
            bodacc_flagged = q(f"SELECT COUNT(*) FROM {SILVER_TABLE} WHERE bodacc_recent = true")
        except Exception:
            pass
        try:
            pappers_total = q(f"SELECT COUNT(*) FROM {PAPPERS_TABLE}")
        except Exception:
            pass
        cur.close(); conn.close()
        return {
            "bronze_total": bronze, "silver_eligible": silver,
            "silver_enriched": enriched, "silver_avg_score": avg_score,
            "bodacc_total": bodacc_total, "bodacc_flagged_silver": bodacc_flagged,
            "pappers_total": pappers_total,
        }
    except Exception as e:
        print(f"[Stats] Postgres MotherDuck failed: {e}")
        return None


async def api_bronze_stats() -> dict:
    """Utilisé par GET /api/admin/bronze-stats."""
    # Priorité : Postgres endpoint (contourne le bug JWT DuckDB extension)
    pg = await asyncio.to_thread(_pg_stats)
    if pg:
        return {**pg, "pipeline": _PIPELINE_STATUS}

    # Fallback DuckDB local
    if not _DUCKDB_OK:
        return {"error": "duckdb non installé", "pipeline": _PIPELINE_STATUS}
    try:
        con = _get_connection()
        bronze   = con.execute(f"SELECT COUNT(*) FROM {BRONZE_TABLE}").fetchone()[0]
        silver   = con.execute(f"SELECT COUNT(*) FROM {SILVER_TABLE}").fetchone()[0]
        enriched = con.execute(f"SELECT COUNT(*) FROM {SILVER_TABLE} WHERE enriched = true").fetchone()[0]
        avg_score = con.execute(f"SELECT ROUND(AVG(ma_score)) FROM {SILVER_TABLE}").fetchone()[0]
        bodacc_total = bodacc_flagged = pappers_total = 0
        try:
            bodacc_total  = con.execute(f"SELECT COUNT(*) FROM {BODACC_TABLE}").fetchone()[0]
            bodacc_flagged = con.execute(f"SELECT COUNT(*) FROM {SILVER_TABLE} WHERE bodacc_recent = true").fetchone()[0]
        except Exception:
            pass
        try:
            pappers_total = con.execute(f"SELECT COUNT(*) FROM {PAPPERS_TABLE}").fetchone()[0]
        except Exception:
            pass
        con.close()
        return {
            "bronze_total": bronze, "silver_eligible": silver,
            "silver_enriched": enriched, "silver_avg_score": avg_score,
            "bodacc_total": bodacc_total, "bodacc_flagged_silver": bodacc_flagged,
            "pappers_total": pappers_total, "pipeline": _PIPELINE_STATUS,
        }
    except Exception as e:
        return {"error": str(e), "pipeline": _PIPELINE_STATUS}


# =============================================================================
# CLI
# =============================================================================

async def _run_async(cmd: str, args: list[str]) -> None:
    if cmd == "setup":
        setup_tables()

    elif cmd == "load-bronze":
        load_bronze()

    elif cmd == "build-silver":
        build_silver()

    elif cmd == "load-bodacc":
        since = args[0] if args else "2023-01-01"
        load_bodacc(since=since)

    elif cmd == "flag-bodacc":
        flag_bodacc_silver()

    elif cmd == "stats":
        print_stats()

    elif cmd == "sync-supabase":
        top_n = int(args[0]) if args else 5000
        prio  = args[1] if len(args) > 1 else "score"
        await sync_silver_to_supabase(top_n=top_n, priority=prio)

    elif cmd == "load-pappers":
        load_pappers_bronze()

    elif cmd == "enrich-pappers":
        enrich_silver_pappers()

    elif cmd == "full":
        setup_tables()
        load_bronze()
        build_silver()
        load_bodacc()
        flag_bodacc_silver()
        load_pappers_bronze()
        enrich_silver_pappers()
        await sync_silver_to_supabase(top_n=5000, priority="bodacc")

    else:
        print(__doc__)


if __name__ == "__main__":
    cmd  = sys.argv[1] if len(sys.argv) > 1 else "help"
    args = sys.argv[2:]
    asyncio.run(_run_async(cmd, args))
