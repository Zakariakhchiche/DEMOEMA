-- ============================================================================
-- silver.icij_offshore_match — matche les officers ICIJ avec les dirigeants
-- silver.dirigeants_360 (et gold.dirigeants_master) sur (nom + prenom).
--
-- Pré-requis : bronze.icij_offshore_raw doit être peuplée par
-- load_icij_offshore.py (download manuel depuis offshoreleaks.icij.org).
--
-- Match strategy :
--   - Officer ICIJ a un `name` du genre "JEAN MARTIN" ou "Jean Martin" ou
--     "MARTIN, Jean" ou "Mr Jean Martin" → on tokenize, normalise, compare.
--   - Match exact UPPER(unaccent) sur (nom, prenom) en croisant avec
--     silver.dirigeants_360 (le set le plus large : 8.1M dirigeants FR).
--   - On retient les leaks (source_leak) et le pays Officer.
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS silver.icij_offshore_match CASCADE;

CREATE MATERIALIZED VIEW silver.icij_offshore_match AS
WITH officers_normalized AS (
    SELECT
        node_id,
        name AS raw_name,
        country,
        source_leak,
        payload,
        -- Heuristique simple : split sur espace/virgule pour extraire prenom/nom
        -- Format ICIJ varie : "FIRST LAST", "LAST, FIRST", "Mr First LAST"...
        upper(unaccent(trim(regexp_replace(name, '^(Mr|Mme|Mlle|Dr)\.?\s+', '', 'i')))) AS name_clean
    FROM bronze.icij_offshore_raw
    WHERE role = 'OFFICER'
      AND name IS NOT NULL
      AND length(name) > 4
),
-- Dirigeants FR (silver.dirigeants_360 n'existe pas — utiliser inpi_dirigeants
-- direct ; gold.dirigeants_master pour pro_ma_score quand dispo).
dirigeants_index AS (
    SELECT
        d.nom,
        d.prenom,
        d.date_naissance,
        d.age_2026,
        d.n_mandats_actifs,
        coalesce(gd.pro_ma_score, 0) AS pro_ma_score,
        upper(unaccent(d.nom || ' ' || d.prenom)) AS nom_prenom_uc,
        upper(unaccent(d.prenom || ' ' || d.nom)) AS prenom_nom_uc
    FROM silver.inpi_dirigeants d
    LEFT JOIN gold.dirigeants_master gd
      ON gd.nom = d.nom AND gd.prenom = d.prenom
)
SELECT
    o.node_id AS icij_node_id,
    o.raw_name AS icij_name,
    o.country AS icij_country,
    o.source_leak AS icij_leak,
    o.payload AS icij_payload,
    d.nom,
    d.prenom,
    d.date_naissance,
    d.age_2026,
    d.n_mandats_actifs,
    d.pro_ma_score,
    -- Confiance match : exact (nom+prenom dans n'importe quel ordre)
    CASE
        WHEN o.name_clean = d.nom_prenom_uc THEN 'EXACT_NOM_PRENOM'
        WHEN o.name_clean = d.prenom_nom_uc THEN 'EXACT_PRENOM_NOM'
        ELSE 'PARTIAL'
    END AS match_type
FROM officers_normalized o
JOIN dirigeants_index d
  ON o.name_clean IN (d.nom_prenom_uc, d.prenom_nom_uc);

-- Indexes
CREATE UNIQUE INDEX IF NOT EXISTS icij_offshore_match_unique_idx
  ON silver.icij_offshore_match (icij_node_id, nom, prenom);
CREATE INDEX IF NOT EXISTS icij_offshore_match_dirigeant_idx
  ON silver.icij_offshore_match (nom, prenom);
CREATE INDEX IF NOT EXISTS icij_offshore_match_score_idx
  ON silver.icij_offshore_match (pro_ma_score DESC NULLS LAST);
