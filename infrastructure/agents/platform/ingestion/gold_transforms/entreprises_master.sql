SET statement_timeout = 0;
DROP TABLE IF EXISTS gold.entreprises_master CASCADE;

CREATE TABLE gold.entreprises_master AS
WITH lei_dedup AS (
    SELECT DISTINCT ON (siren_fr) siren_fr, lei
    FROM silver.gleif_lei
    WHERE siren_fr IS NOT NULL
    ORDER BY siren_fr, lei DESC
),
iul_dedup AS (
    SELECT DISTINCT ON (siren) siren, tranche_effectifs, categorie_juridique, etat_administratif
    FROM silver.insee_unites_legales
    ORDER BY siren, date_derniere_maj DESC NULLS LAST
)
SELECT
    es.siren,
    es.denomination,
    es.forme_juridique,
    es.code_ape,
    es.sigle,
    es.nom_commercial,
    es.adresse_code_postal,
    es.adresse_commune,
    es.adresse_dept,
    es.adresse_voie,
    es.adresse_pays,
    es.date_immatriculation,
    es.date_debut_activite,
    es.age_entreprise,
    es.effectif_salarie,
    es.capital_social,
    es.age_dirigeant_max,
    es.has_dirigeant_senior,
    es.n_sci_dirigeants,
    es.total_capital_sci,
    es.has_holding_patrimoniale,
    es.n_mandats_dirigeant_max,
    es.has_pro_ma,
    es.n_dirigeants,
    es.ca_latest,
    es.capitaux_propres_latest,
    es.resultat_net_latest,
    es.n_exercices_deposes,
    es.has_bilan_recent,
    es.effectif_moyen_latest,
    es.immo_corporelles,
    es.immo_corporelles_high,
    es.has_late_filing,
    lei.lei AS lei,
    iul.tranche_effectifs AS insee_tranche_effectifs,
    iul.categorie_juridique AS insee_categorie_juridique,
    iul.etat_administratif AS insee_etat_administratif,
    LEAST(100, GREATEST(0,
        50
        + CASE WHEN es.has_pro_ma THEN 10 ELSE 0 END
        + CASE WHEN es.has_holding_patrimoniale THEN 10 ELSE 0 END
        + CASE WHEN es.has_dirigeant_senior THEN 10 ELSE 0 END
        + CASE WHEN es.has_bilan_recent THEN 5 ELSE 0 END
        + LEAST(15, GREATEST(0, COALESCE(es.ca_latest, 0) / 1000000.0))::int
        - CASE WHEN es.has_late_filing THEN 10 ELSE 0 END
        - CASE WHEN COALESCE(es.resultat_net_latest, 0) < 0 THEN 5 ELSE 0 END
    ))::int AS pro_ma_score,
    NOW() AS materialized_at
FROM silver.entreprises_signals es
LEFT JOIN iul_dedup iul ON iul.siren = es.siren
LEFT JOIN lei_dedup lei ON lei.siren_fr = es.siren;

CREATE INDEX ON gold.entreprises_master (siren);
CREATE INDEX ON gold.entreprises_master (pro_ma_score DESC);
CREATE INDEX ON gold.entreprises_master (ca_latest DESC NULLS LAST);
CREATE INDEX ON gold.entreprises_master (code_ape);
CREATE INDEX ON gold.entreprises_master (adresse_dept);
CREATE INDEX ON gold.entreprises_master (has_pro_ma) WHERE has_pro_ma = true;

