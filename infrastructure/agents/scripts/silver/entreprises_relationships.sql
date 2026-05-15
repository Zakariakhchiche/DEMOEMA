-- Vue silver des relations parent-filiale + dirigeants étrangers, agrégée
-- depuis 3 sources :
-- 1. INPI personnes morales (1.77M relations FR→FR + parent étranger)
-- 2. GLEIF parent_lei (sparse mais utile pour grands groupes cotés)
-- 3. INPI individus avec adresse étrangère (signal expat business)

BEGIN;

DROP MATERIALIZED VIEW IF EXISTS silver.entreprises_relationships CASCADE;

CREATE MATERIALIZED VIEW silver.entreprises_relationships AS
WITH inpi_parents AS (
  -- Société X (entreprise_siren) est dirigeante de la société Y (siren)
  SELECT DISTINCT
    siren AS child_siren,
    entreprise_siren AS parent_siren,
    entreprise_denomination AS parent_denomination,
    UPPER(COALESCE(entreprise_pays, 'FRA')) AS parent_country,
    'inpi_dirigeant_morale' AS source,
    role_entreprise AS role_code
  FROM bronze.inpi_formalites_personnes
  WHERE type_de_personne = 'ENTREPRISE'
    AND entreprise_siren IS NOT NULL
    AND siren IS NOT NULL
    AND length(trim(entreprise_siren)) >= 4  -- minimum sanity (excl. NULL/empty)
),
gleif_parents AS (
  -- GLEIF parent (sparse mais certifié, utile groupes cotés)
  SELECT DISTINCT
    child.siren_fr AS child_siren,
    parent.siren_fr AS parent_siren,
    parent.legal_name AS parent_denomination,
    UPPER(COALESCE(parent.country_code, 'XXX')) AS parent_country,
    'gleif_parent' AS source,
    NULL::text AS role_code
  FROM silver.gleif_lei child
  JOIN silver.gleif_lei parent ON parent.lei = child.parent_lei
  WHERE child.siren_fr IS NOT NULL
    AND child.parent_lei IS NOT NULL
)
SELECT * FROM inpi_parents
UNION ALL
SELECT * FROM gleif_parents;

CREATE INDEX entreprises_relationships_child_idx
  ON silver.entreprises_relationships (child_siren);
CREATE INDEX entreprises_relationships_parent_idx
  ON silver.entreprises_relationships (parent_siren);
CREATE INDEX entreprises_relationships_country_idx
  ON silver.entreprises_relationships (parent_country);

ANALYZE silver.entreprises_relationships;

COMMIT;
