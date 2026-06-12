# Roadmap — Sweep 16 Millions d'Entités INSEE SIRENE

## Contexte

La plateforme accède aujourd'hui à **~300 cibles M&A** via des recherches paginées
sur l'API Recherche Entreprises (gouv.fr). Cette API ne permet pas de paginer
au-delà de 25 résultats par appel — elle est conçue pour la recherche unitaire,
pas pour le bulk.

L'INSEE publie en open data la **base SIRENE complète** : ~16 millions d'entités
légales françaises (SIRENs + SIRETs). Ce fichier est la source primaire de toutes
les APIs gouvernementales — il n'y a pas de meilleure source pour un sweep exhaustif.

**Objectif** : passer de ~300 cibles à **50 000+ PME/ETI M&A-éligibles** en base,
accessibles instantanément sans appels API, enrichies à la demande.

---

## Les données disponibles

### Fichier SIRENE stock (recommandé)

```
Producteur : INSEE
URL        : https://www.data.gouv.fr/fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret/
Format     : 2 fichiers CSV compressés (.gz) mis à jour chaque mois
  - StockUniteLegale_utf8.csv.gz       (~2.5 Go, ~15M lignes) — 1 ligne/SIREN
  - StockEtablissement_utf8.csv.gz     (~5 Go, ~30M lignes)   — 1 ligne/SIRET
Auth       : Aucune
Quota      : Aucun — bulk download public
Fréquence  : Mise à jour mensuelle (J+3 après fin de mois)
```

**Champs utiles pour filtrage M&A :**

| Champ | Description | Filtre |
|-------|-------------|--------|
| `siren` | Identifiant entreprise | Clé primaire |
| `denominationUniteLegale` | Nom officiel | — |
| `activitePrincipaleUniteLegale` | Code NAF (APE) | `IN (_LOAD_PROFILES.code_naf)` |
| `categorieEntreprise` | PME / ETI / GE | `IN ('PME', 'ETI')` |
| `etatAdministratifUniteLegale` | A = active / F = fermée | `= 'A'` |
| `dateCreationUniteLegale` | Date création | ancienneté > 3 ans |
| `trancheEffectifsUniteLegale` | Code effectif INSEE | `>= '11'` (10–19 sal.) |
| `categorieJuridiqueUniteLegale` | Forme juridique | `IN ('5498','5499','5410','5599'…)` → SAS/SARL/SA |

**Volume estimé après filtrage :**
- Entreprises actives total : ~11M
- PME + ETI : ~3.5M
- PME/ETI actives avec 10+ salariés : ~500 000
- PME/ETI dans les NAF cibles Origin (62 codes) : **~50 000–80 000**

### BODACC bulk events (signal-driven)

```
Source  : BODACC OpenDataSoft — export dataset complet
URL     : https://bodacc-datadila.opendatasoft.com/explore/dataset/annonces-commerciales/export/
Format  : CSV / JSON export
Volume  : 48.8M annonces (toutes catégories)
Filtre  : typeavis_lib = "Cession" (derniers 90 jours) → ~3 000–5 000 SIRENs/mois
Valeur  : Ces entreprises ont des événements M&A déclarés = signal qualité maximale
```

---

## Architecture cible

```
┌──────────────────────────────────────────────────────────────┐
│  PHASE 0 — Existant (en prod)                                 │
│  62 profils NAF × BODACC hot SIRENs → ~300 cibles enrichies  │
│  Stockées dans Supabase (enriched_targets)                    │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────┐
│  PHASE 1 — SIRENE Index (à implémenter)                       │
│                                                               │
│  Cron mensuel → download StockUniteLegale.csv.gz              │
│  → filter_ma_eligible() → ~50K SIRENs                        │
│  → Supabase table sirene_index                                │
│    (siren, naf, dept, effectif, date_creation,                │
│     bodacc_recent, ma_score_estimate, enriched)               │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────┐
│  PHASE 2 — Enrichissement progressif (à implémenter)          │
│                                                               │
│  Worker async — /api/admin/enrich-batch?n=50                  │
│  Priorisation : bodacc_recent DESC, ma_score_estimate DESC     │
│  → get_full_company_info() → build_target()                   │
│  → enriched_targets (Supabase)                                │
│  Rythme : 50 entreprises/appel, respecte 7 req/s              │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────┐
│  RÉSULTAT                                                     │
│  ~50K cibles indexées → ~5K enrichies (top priorité)         │
│  Accessible via /api/targets avec filtres NAF/dept/score      │
└──────────────────────────────────────────────────────────────┘
```

---

## Tâches concrètes

### Tâche 1 — `backend/sirene_bulk.py`

```python
# Fonctions à créer :

async def download_sirene_stock(dest_dir: str = "/tmp") -> str:
    """Télécharge StockUniteLegale_utf8.csv.gz depuis data.gouv.fr.
    Retourne le chemin du fichier décompressé."""
    URL = "https://files.data.gouv.fr/insee-sirene/StockUniteLegale_utf8.csv.gz"
    # httpx stream → fichier local → gzip decompress
    ...

def filter_ma_eligible(csv_path: str, naf_codes: set[str]) -> list[dict]:
    """Parse le CSV SIRENE ligne par ligne (streaming).
    Filtre : actives + PME/ETI + effectif >= '11' + NAF cibles.
    Retourne liste de {siren, naf, dept, effectif, date_creation}."""
    # pandas chunked read ou csv.DictReader pour faible mémoire
    ...

async def upsert_sirene_index(rows: list[dict]) -> int:
    """Upsert batch dans Supabase table sirene_index.
    Retourne nombre de lignes insérées/mises à jour."""
    ...

async def score_bodacc_recent(sirens: list[str]) -> dict[str, bool]:
    """Pour chaque SIREN, vérifie s'il a une annonce BODACC récente (90j).
    Met à jour le champ bodacc_recent dans sirene_index."""
    ...
```

### Tâche 2 — Schema Supabase `sirene_index`

```sql
-- À exécuter dans Supabase SQL editor

CREATE TABLE IF NOT EXISTS sirene_index (
  siren               TEXT PRIMARY KEY,
  naf                 TEXT,
  dept                TEXT,
  effectif_tranche    TEXT,
  date_creation       DATE,
  denomination        TEXT,
  categorie_entreprise TEXT,
  bodacc_recent       BOOLEAN DEFAULT false,
  ma_score_estimate   SMALLINT DEFAULT 0,
  enriched            BOOLEAN DEFAULT false,
  enriched_at         TIMESTAMPTZ,
  created_at          TIMESTAMPTZ DEFAULT now(),
  updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sirene_index_enriched
  ON sirene_index (enriched, ma_score_estimate DESC);

CREATE INDEX IF NOT EXISTS idx_sirene_index_naf
  ON sirene_index (naf);

CREATE INDEX IF NOT EXISTS idx_sirene_index_dept
  ON sirene_index (dept);
```

### Tâche 3 — Endpoint `/api/admin/rebuild-index`

```python
# Dans main.py

@app.get("/api/admin/rebuild-index")
async def rebuild_sirene_index(secret: str, background_tasks: BackgroundTasks):
    """Déclenche le rebuild complet de sirene_index.
    Lance en background pour ne pas bloquer la réponse HTTP.
    Progress streamé via SSE sur /api/admin/rebuild-index/progress"""
    if secret != os.environ.get("ADMIN_SECRET", "edrcf-admin"):
        raise HTTPException(403)
    background_tasks.add_task(_run_sirene_rebuild)
    return {"status": "started", "message": "Rebuild SIRENE lancé en background"}

async def _run_sirene_rebuild():
    from sirene_bulk import download_sirene_stock, filter_ma_eligible, upsert_sirene_index
    naf_codes = {p["code_naf"].replace(".", "") for p in _LOAD_PROFILES}
    csv_path = await download_sirene_stock()
    rows = filter_ma_eligible(csv_path, naf_codes)
    inserted = await upsert_sirene_index(rows)
    print(f"[SIRENE] Rebuild complete: {inserted} lignes dans sirene_index")
```

### Tâche 4 — Endpoint `/api/admin/enrich-batch`

```python
@app.get("/api/admin/enrich-batch")
async def enrich_batch(n: int = 50, secret: str = ""):
    """Enrichit N entreprises depuis sirene_index (non enrichies, priorité score).
    Rate-limited à 7 req/s via asyncio.sleep entre appels."""
    if secret != os.environ.get("ADMIN_SECRET", "edrcf-admin"):
        raise HTTPException(403)

    # Récupérer les N SIRENs les plus prioritaires non enrichis
    rows = supabase.table("sirene_index")\
        .select("siren")\
        .eq("enriched", False)\
        .order("ma_score_estimate", desc=True)\
        .order("bodacc_recent", desc=True)\
        .limit(n)\
        .execute()

    results = {"enriched": 0, "failed": 0}
    for row in rows.data:
        siren = row["siren"]
        try:
            company_info = await get_full_company_info(siren)
            if company_info:
                target = build_target(idx=0, company_info=company_info, search_info={})
                enriched_targets.append(target)
                # Marquer comme enrichi
                supabase.table("sirene_index")\
                    .update({"enriched": True, "enriched_at": "now()"})\
                    .eq("siren", siren)\
                    .execute()
                results["enriched"] += 1
        except Exception:
            results["failed"] += 1
        await asyncio.sleep(1 / 7)  # respect 7 req/s

    return results
```

---

## Score pré-filtrage (pre-enrichment scoring)

Avant l'enrichissement complet (coûteux en API calls), calculer un score rapide
basé uniquement sur les données SIRENE pour prioriser les 50K :

```python
def compute_ma_score_estimate(row: dict) -> int:
    """Score 0-100 calculé sans appel API — données SIRENE uniquement."""
    score = 0

    # Effectif : PME/ETI 10-500 salariés = sweet spot M&A
    tranche = row.get("trancheEffectifsUniteLegale", "")
    if tranche in ("11", "12"):   score += 20   # 10-49
    elif tranche in ("21", "22"): score += 25   # 50-199
    elif tranche in ("31", "32"): score += 20   # 200-499
    elif tranche in ("41",):      score += 15   # 500-999

    # Ancienneté : 5-20 ans = maturité + succession potentielle
    try:
        age = 2026 - int(row.get("dateCreationUniteLegale", "2020")[:4])
        if 5 <= age <= 10:   score += 15
        elif 10 < age <= 20: score += 20
        elif age > 20:       score += 10
    except Exception:
        pass

    # Forme juridique : SAS/SARL/SA = structures M&A classiques
    cj = row.get("categorieJuridiqueUniteLegale", "")
    if cj in ("5498", "5499", "5710", "5720"):  score += 15  # SAS/SASU
    elif cj in ("5410", "5422"):                score += 12  # SARL/EURL
    elif cj in ("5599", "5505", "5510"):        score += 10  # SA

    # BODACC récent : signal M&A fort
    if row.get("bodacc_recent"):                score += 25

    return min(score, 100)
```

---

## Plan de déploiement

| Étape | Priorité | Durée estimée |
|-------|----------|---------------|
| Créer `sirene_bulk.py` + tests | Haute | 1 jour |
| Créer table `sirene_index` Supabase | Haute | 30 min |
| Endpoint `rebuild-index` + background task | Haute | 1 jour |
| Endpoint `enrich-batch` | Haute | 1/2 jour |
| Score pré-filtrage | Moyenne | 1/2 jour |
| Cron mensuel rebuild | Moyenne | 1h |
| Pagination Targets par sirene_index | Moyenne | 1 jour |
| Interface analyst (bulk enrich depuis UI) | Basse | 1 jour |

---

## Quotas et limitations

| API | Quota | Stratégie |
|-----|-------|-----------|
| Fichier SIRENE CSV | Aucun | Download mensuel, ~4 Go |
| API Recherche Entreprises | 7 req/s | `asyncio.sleep(1/7)` entre calls |
| BODACC OpenDataSoft | 10 000 req/jour | Batch nocturne uniquement |
| INPI RNE | 10 000 req/jour | Optionnel, pour enrichissement dirigeants |
| Supabase Free | 500 MB storage, 50K rows | Table index séparée, GZIP si besoin |

---

## Sources de référence

- Fichier SIRENE mensuel : data.gouv.fr/fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret
- Documentation champs SIRENE : insee.fr/fr/information/2028359
- Signaux Faibles (scoring défaillance similaire) : github.com/signaux-faibles
- Open Food Facts (modèle bulk download + enrichissement progressif) : github.com/openfoodfacts
