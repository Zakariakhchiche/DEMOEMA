SET statement_timeout = 0;
DROP MATERIALIZED VIEW IF EXISTS silver.entreprises_signals CASCADE;

CREATE MATERIALIZED VIEW silver.entreprises_signals AS
WITH cibles AS (
    SELECT
        siren,
        denomination,
        forme_juridique,
        code_ape,
        sigle,
        nom_commercial,
        adresse_code_postal,
        adresse_commune,
        LEFT(adresse_code_postal, 2) AS adresse_dept,
        adresse_voie,
        adresse_pays,
        date_immatriculation,
        date_debut_activite,
        EXTRACT(YEAR FROM AGE(now(), date_immatriculation::timestamp))::int AS age_entreprise,
        effectif_salarie,
        montant_capital
    FROM (SELECT DISTINCT ON (siren) * FROM bronze.inpi_formalites_entreprises ORDER BY siren, date_immatriculation DESC NULLS LAST) AS bie
    WHERE forme_juridique IN (
        $$5710$$, $$5720$$, $$5730$$, $$5485$$, $$5499$$, $$5505$$,
        $$5510$$, $$5515$$, $$5520$$, $$5530$$, $$5540$$, $$5599$$,
        $$5385$$, $$5308$$, $$5306$$, $$5202$$, $$5203$$
    )
      AND montant_capital >= 100000
      AND date_radiation IS NULL
),
dernier_bilan AS (
    SELECT DISTINCT ON (siren)
        siren,
        ca_net AS ca_latest,
        capitaux_propres AS capitaux_propres_latest,
        resultat_net AS resultat_net_latest,
        date_cloture AS bilan_date_cloture,
        date_depot AS bilan_date_depot,
        effectif_moyen AS effectif_moyen_latest,
        ca_net,
        immo_corporelles,
        total_actif,
        total_passif
    FROM silver.inpi_comptes
    ORDER BY siren, date_cloture DESC NULLS LAST
),
dirigeants_par_siren AS (
    SELECT
        siren_unnest.siren AS siren,
        d.nom,
        d.prenom,
        d.age_2026,
        d.n_mandats_actifs,
        d.n_sci,
        d.total_capital_sci
    FROM silver.inpi_dirigeants d
    CROSS JOIN LATERAL unnest(d.sirens_mandats) AS siren_unnest(siren)
),
agg_dirigeants AS (
    SELECT
        siren,
        MAX(age_2026) AS age_dirigeant_max,
        SUM(n_sci) AS n_sci_dirigeants,
        SUM(total_capital_sci) AS total_capital_sci,
        MAX(n_mandats_actifs) AS n_mandats_dirigeant_max,
        COUNT(*) AS n_dirigeants
    FROM dirigeants_par_siren
    WHERE siren IN (SELECT siren FROM cibles)
    GROUP BY siren
),
n_exercices AS (
    SELECT siren, count(DISTINCT date_cloture) AS n_exercices_deposes
    FROM silver.inpi_comptes
    GROUP BY siren
)
SELECT
    c.siren,
    c.denomination,
    c.forme_juridique,
    c.code_ape,
    c.sigle,
    c.nom_commercial,
    c.adresse_code_postal,
    c.adresse_commune,
    c.adresse_dept,
    c.adresse_voie,
    c.adresse_pays,
    c.date_immatriculation,
    c.date_debut_activite,
    c.age_entreprise,
    c.effectif_salarie,
    c.montant_capital AS capital_social,
    -- Dirigeants
    a.age_dirigeant_max,
    (a.age_dirigeant_max IS NOT NULL AND a.age_dirigeant_max >= 60) AS has_dirigeant_senior,
    a.n_sci_dirigeants,
    a.total_capital_sci,
    (COALESCE(a.n_sci_dirigeants, 0) >= 2) AS has_holding_patrimoniale,
    a.n_mandats_dirigeant_max,
    (COALESCE(a.n_mandats_dirigeant_max, 0) >= 5) AS has_pro_ma,
    a.n_dirigeants,
    -- Financier
    b.ca_latest,
    b.capitaux_propres_latest,
    b.resultat_net_latest,
    ne.n_exercices_deposes,
    (b.bilan_date_cloture IS NOT NULL AND b.bilan_date_cloture > now()::date - interval $$2 years$$) AS has_bilan_recent,
    b.effectif_moyen_latest,
    b.immo_corporelles,
    (b.total_actif > 0 AND b.immo_corporelles / NULLIF(b.total_actif, 0) > 0.3) AS immo_corporelles_high,
    -- Filing latency
    (b.bilan_date_depot IS NOT NULL AND b.bilan_date_cloture IS NOT NULL AND b.bilan_date_depot > b.bilan_date_cloture + interval $$7 months$$) AS has_late_filing,
    -- Signaux à enrichir plus tard (NULL pour l instant)
    NULL::int AS n_contentieux,
    NULL::boolean AS has_contentieux_recent,
    NULL::boolean AS has_sanction,
    NULL::boolean AS has_sanction_dirigeant,
    NULL::int AS n_press_mentions_90d,
    NULL::boolean AS has_cession_detected,
    NULL::int AS digital_presence_score,
    NULL::boolean AS has_website,
    NULL::boolean AS has_brevets,
    NULL::boolean AS has_marques,
    NULL::boolean AS has_published_ges_recent,
    NULL::numeric AS emissions_total_tco2e,
    NULL::numeric AS ca_export_ratio,
    NULL::boolean AS has_filiale_etranger,
    NULL::boolean AS has_lei_code,
    NULL::int AS n_marches_publics,
    NULL::numeric AS total_montant_marches,
    NULL::boolean AS is_dependant_commande_publique,
    NULL::boolean AS has_offshore_link,
    NULL::boolean AS is_lobbying_registered,
    NULL::numeric AS chiffre_affaires_lobbying,
    NULL::boolean AS has_kol_pharma,
    NULL::boolean AS has_treasury_excess,
    NULL::boolean AS has_successeur_probable,
    now() AS materialized_at
FROM cibles c
LEFT JOIN agg_dirigeants a ON a.siren = c.siren
LEFT JOIN dernier_bilan b ON b.siren = c.siren
LEFT JOIN n_exercices ne ON ne.siren = c.siren;

CREATE INDEX ON silver.entreprises_signals (siren);
CREATE INDEX ON silver.entreprises_signals (ca_latest DESC NULLS LAST);
CREATE INDEX ON silver.entreprises_signals (age_dirigeant_max DESC NULLS LAST);
CREATE INDEX ON silver.entreprises_signals (code_ape);
CREATE INDEX ON silver.entreprises_signals (adresse_dept);
CREATE INDEX ON silver.entreprises_signals (has_pro_ma) WHERE has_pro_ma = true;
CREATE INDEX ON silver.entreprises_signals (has_holding_patrimoniale) WHERE has_holding_patrimoniale = true;
