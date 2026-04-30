-- silver.hatvp_lobbying v2 — extraire siren depuis payload jsonb
-- Bug rapport QA v4 §3.10 : silver.hatvp_lobbying = 0 rows alors que
-- bronze.hatvp_representants_raw = 459 750 rows. Le silver original
-- filtrait WHERE siren IS NOT NULL mais la colonne siren bronze est
-- toujours NULL (pas extraite du payload).
SET statement_timeout = 0;
DROP MATERIALIZED VIEW IF EXISTS silver.hatvp_lobbying CASCADE;

CREATE MATERIALIZED VIEW silver.hatvp_lobbying AS
SELECT DISTINCT ON (representant_id)
    representant_id,
    COALESCE(
        NULLIF(TRIM(siren), ''),
        payload->>'identifiant_national',
        payload->>'siren'
    )::text AS siren,
    COALESCE(
        NULLIF(TRIM(denomination), ''),
        payload->>'denomination',
        payload->>'nom'
    ) AS denomination,
    COALESCE(
        NULLIF(TRIM(secteur_activite), ''),
        payload->>'secteurs_activite'
    ) AS secteur_activite,
    date_inscription,
    COALESCE(
        NULLIF(TRIM(adresse_ville), ''),
        payload->>'adresse_ville'
    ) AS adresse_ville,
    nb_deputes,
    chiffre_affaires_lobbying,
    (date_inscription >= CURRENT_DATE - INTERVAL '2 years') AS has_active_lobbying,
    payload,
    ingested_at
FROM bronze.hatvp_representants_raw
ORDER BY representant_id, ingested_at DESC;

CREATE INDEX ON silver.hatvp_lobbying (representant_id);
CREATE INDEX ON silver.hatvp_lobbying (siren);
CREATE INDEX ON silver.hatvp_lobbying (secteur_activite);
CREATE INDEX ON silver.hatvp_lobbying (has_active_lobbying);
ANALYZE silver.hatvp_lobbying;
