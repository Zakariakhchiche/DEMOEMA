-- ============================================================================
-- EdRCF 6.0 — Migration : sirene_index
-- Table d'index des PME/ETI M&A-éligibles extraites du fichier SIRENE INSEE
-- Source : ~16M entités → ~50 000-80 000 après filtrage NAF + effectif + statut
--
-- À exécuter dans Supabase → SQL Editor
-- ============================================================================

-- Table principale
CREATE TABLE IF NOT EXISTS sirene_index (
  siren                 TEXT PRIMARY KEY,
  denomination          TEXT,
  naf                   TEXT,
  dept                  TEXT,
  effectif_tranche      TEXT,            -- code INSEE ex: '11'=10-19 sal.
  date_creation         DATE,
  categorie_juridique   TEXT,            -- code INSEE ex: '5498'=SAS
  categorie_entreprise  TEXT,            -- PME / ETI
  bodacc_recent         BOOLEAN  DEFAULT false,
  ma_score_estimate     SMALLINT DEFAULT 0,   -- score 0-100 pré-enrichissement
  enriched              BOOLEAN  DEFAULT false,
  enriched_at           TIMESTAMPTZ,
  created_at            TIMESTAMPTZ DEFAULT now(),
  updated_at            TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE sirene_index IS
  'Index des PME/ETI françaises M&A-éligibles. '
  'Alimenté par sirene_bulk.py depuis le fichier SIRENE INSEE mensuel (~16M lignes). '
  'Utilisé pour prioriser les enrichissements vers enriched_targets.';

COMMENT ON COLUMN sirene_index.ma_score_estimate IS
  'Score 0-100 calculé sans appel API (effectif, ancienneté, forme juridique, catégorie). '
  'Augmenté de +25 si bodacc_recent=true.';

COMMENT ON COLUMN sirene_index.bodacc_recent IS
  'True si une annonce BODACC (cession, modification) existe dans les 90 derniers jours. '
  'Signal M&A fort — ces entreprises sont prioritaires pour l''enrichissement.';

-- ── Index pour requêtes fréquentes ─────────────────────────────────────────

-- Requête principale : "donne-moi les N SIRENs non enrichis, les plus intéressants"
CREATE INDEX IF NOT EXISTS idx_sirene_to_enrich
  ON sirene_index (enriched, bodacc_recent DESC, ma_score_estimate DESC);

-- Filtrage par secteur NAF
CREATE INDEX IF NOT EXISTS idx_sirene_naf
  ON sirene_index (naf);

-- Filtrage par département
CREATE INDEX IF NOT EXISTS idx_sirene_dept
  ON sirene_index (dept);

-- Filtrage par score
CREATE INDEX IF NOT EXISTS idx_sirene_score
  ON sirene_index (ma_score_estimate DESC);

-- ── Trigger updated_at automatique ────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_sirene_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sirene_updated_at ON sirene_index;
CREATE TRIGGER trg_sirene_updated_at
  BEFORE UPDATE ON sirene_index
  FOR EACH ROW EXECUTE FUNCTION update_sirene_updated_at();

-- ── Vue stats rapides ──────────────────────────────────────────────────────

CREATE OR REPLACE VIEW sirene_index_stats AS
SELECT
  COUNT(*)                                        AS total,
  COUNT(*) FILTER (WHERE enriched = true)         AS enriched_count,
  COUNT(*) FILTER (WHERE enriched = false)        AS to_enrich,
  COUNT(*) FILTER (WHERE bodacc_recent = true)    AS bodacc_hot,
  COUNT(*) FILTER (WHERE ma_score_estimate >= 60) AS high_score,
  COUNT(*) FILTER (WHERE ma_score_estimate >= 40) AS medium_score,
  ROUND(AVG(ma_score_estimate))                   AS avg_score,
  COUNT(DISTINCT naf)                             AS distinct_naf_codes,
  COUNT(DISTINCT dept)                            AS distinct_depts
FROM sirene_index;

COMMENT ON VIEW sirene_index_stats IS
  'Stats agrégées de sirene_index. Requête via: SELECT * FROM sirene_index_stats;';

-- ── Requêtes utiles (commentées pour référence) ────────────────────────────

-- Top 50 SIRENs prioritaires non enrichis :
-- SELECT siren, denomination, naf, dept, ma_score_estimate, bodacc_recent
-- FROM sirene_index
-- WHERE enriched = false
-- ORDER BY bodacc_recent DESC, ma_score_estimate DESC
-- LIMIT 50;

-- Répartition par secteur NAF :
-- SELECT naf, COUNT(*) AS nb, AVG(ma_score_estimate)::INT AS avg_score
-- FROM sirene_index
-- GROUP BY naf
-- ORDER BY nb DESC;

-- Répartition par département :
-- SELECT dept, COUNT(*) AS nb
-- FROM sirene_index
-- GROUP BY dept
-- ORDER BY nb DESC
-- LIMIT 20;
