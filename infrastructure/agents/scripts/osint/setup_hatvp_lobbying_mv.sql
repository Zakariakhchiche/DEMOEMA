-- ============================================================================
-- silver.hatvp_lobbying_persons — nouvelle MV exploitant le schema réel de
-- bronze.hatvp_representants_raw (CSV "représentants d'intérêts" HATVP).
--
-- Pourquoi pas réutiliser silver.hatvp_conflits_interets : cette MV existante
-- attend un autre format JSON (déclarations PEP avec champs id/nom/prenom/
-- activites[]/participations[]/mandats[]) qui n'est PAS ce que le fetcher
-- HATVP actuel télécharge. Le bronze actuel a un schema CSV différent
-- (nom_dirigeant/prenom_dirigeant/identifiant_national/denomination/etc).
--
-- Memory rule : "ne jamais drop column" → on laisse l'ancienne MV intacte
-- pour le jour où un fetcher PEP sera ajouté ; on crée une NOUVELLE MV
-- compatible avec le bronze actuel.
--
-- Use case : flag dirigeants notables enregistrés HATVP (lobby) + leur SIREN
-- → croisement avec gold.dirigeants_master / dirigeants_360 via
-- (nom, prenom, siren).
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS silver.hatvp_lobbying_persons AS
SELECT
    -- Identité du dirigeant lobbyiste
    upper(unaccent(payload->>'nom_dirigeant')) AS dirigeant_nom,
    upper(unaccent(payload->>'prenom_dirigeant')) AS dirigeant_prenom,
    payload->>'civilite_dirigeant' AS dirigeant_civilite,
    payload->>'fonction_dirigeant' AS dirigeant_fonction,
    -- Identité du collaborateur (souvent = le déclarant lobbyiste lui-même)
    upper(unaccent(payload->>'nom_collaborateur')) AS collaborateur_nom,
    upper(unaccent(payload->>'prenom_collaborateur')) AS collaborateur_prenom,
    payload->>'fonction_collaborateur' AS collaborateur_fonction,
    -- Société représentée
    payload->>'denomination' AS denomination,
    -- SIREN si type_identifiant_national = 'SIREN' (le filtre WHERE garantit ça)
    nullif(payload->>'identifiant_national', '')::char(9) AS siren,
    payload->>'label_categorie_organisation' AS categorie_organisation,
    payload->>'site_web' AS site_web,
    payload->>'page_linkedin' AS linkedin,
    payload->>'page_twitter' AS twitter,
    -- Métadonnées HATVP
    payload->>'date_premiere_publication' AS date_publication_hatvp,
    payload->>'derniere_publication_activite' AS date_derniere_activite,
    coalesce((payload->>'activites_publiees')::boolean, false) AS lobbying_actif,
    payload AS raw_payload,
    ingested_at
FROM bronze.hatvp_representants_raw
WHERE payload->>'identifiant_national' IS NOT NULL
  AND payload->>'identifiant_national' != ''
  AND payload->>'type_identifiant_national' = 'SIREN'
  AND length(payload->>'identifiant_national') = 9;

-- Index pour le matching dirigeants_360 / gold.dirigeants_master
CREATE UNIQUE INDEX IF NOT EXISTS hatvp_lobbying_persons_unique_idx
  ON silver.hatvp_lobbying_persons (siren, dirigeant_nom, dirigeant_prenom, denomination);
CREATE INDEX IF NOT EXISTS hatvp_lobbying_persons_dirigeant_idx
  ON silver.hatvp_lobbying_persons (dirigeant_nom, dirigeant_prenom);
CREATE INDEX IF NOT EXISTS hatvp_lobbying_persons_collaborateur_idx
  ON silver.hatvp_lobbying_persons (collaborateur_nom, collaborateur_prenom);
CREATE INDEX IF NOT EXISTS hatvp_lobbying_persons_siren_idx
  ON silver.hatvp_lobbying_persons (siren);
