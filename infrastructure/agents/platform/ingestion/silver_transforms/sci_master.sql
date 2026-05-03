-- silver.sci_master — feature store SCI / holdings patrimoniales
-- Hand-written 2026-05-03 (cache pour éviter re-génération LLM Ollama).
-- Spec : silver_specs/sci_master.yaml
--
-- 1 row par siren SCI (forme 65xx) ou holding patrimoniale détectée
-- (SARL/SAS dont denomination contient PATRIMOINE/HOLDING/FAMIL/MAISON).
--
-- Sources :
--   bronze.inpi_formalites_entreprises  -- identité, capital, adresse
--   bronze.inpi_formalites_personnes    -- ownership_type via type_de_personne
--   silver.inpi_comptes                  -- patrimoine financier (dernier bilan)
--   silver.inpi_dirigeants               -- dirigeants individus reverse-lookup
--   silver.dvf_transactions              -- zone DVF par CP

CREATE MATERIALIZED VIEW silver.sci_master AS
WITH

-- ───────── 1. CIBLE : SCIs + holdings patrimoniales ─────────
sci_base AS (
    SELECT DISTINCT ON (e.siren)
        e.siren,
        e.denomination,
        e.forme_juridique,
        e.code_ape,
        e.sigle,
        e.nom_commercial,
        e.adresse_voie,
        e.adresse_code_postal,
        LEFT(e.adresse_code_postal, 2) AS adresse_dept,
        e.adresse_pays,
        e.date_immatriculation,
        e.montant_capital AS capital_social,
        EXTRACT(YEAR FROM AGE(now(), e.date_immatriculation))::int AS age_entreprise,
        (e.forme_juridique LIKE '65%') AS is_sci,
        (e.forme_juridique IN ('5499','5710') AND (
             e.denomination ILIKE '%PATRIMOINE%'
          OR e.denomination ILIKE '%HOLDING%'
          OR e.denomination ILIKE '%FAMIL%'
          OR e.denomination ILIKE '%MAISON %'
        )) AS is_holding_patrimoniale
    FROM bronze.inpi_formalites_entreprises e
    WHERE e.siren IS NOT NULL
      AND (
           e.forme_juridique LIKE '65%'
        OR (e.forme_juridique IN ('5499','5710') AND (
                 e.denomination ILIKE '%PATRIMOINE%'
              OR e.denomination ILIKE '%HOLDING%'
              OR e.denomination ILIKE '%FAMIL%'
              OR e.denomination ILIKE '%MAISON %'
           ))
      )
    ORDER BY e.siren, e.updated_at_src DESC NULLS LAST
),

-- ───────── 2. PATRIMOINE FINANCIER : dernier bilan INPI ─────────
last_bilan AS (
    SELECT DISTINCT ON (c.siren)
        c.siren,
        c.ca_net,
        c.resultat_net,
        c.total_actif,
        c.immo_corporelles,
        c.capitaux_propres,
        c.emprunts_dettes,
        c.effectif_moyen,
        c.date_cloture
    FROM silver.inpi_comptes c
    WHERE c.siren IN (SELECT siren FROM sci_base)
    ORDER BY c.siren, c.date_cloture DESC NULLS LAST
),

-- ───────── 3. OWNERSHIP : count individus vs personnes morales ─────────
ownership AS (
    SELECT
        p.siren,
        count(*) FILTER (WHERE p.type_de_personne = 'INDIVIDU' AND p.actif = true) AS n_dirigeants_individu,
        count(*) FILTER (WHERE p.type_de_personne = 'PERSONNE_MORALE' AND p.actif = true) AS n_dirigeants_morale,
        array_agg(DISTINCT p.entreprise_siren) FILTER (
            WHERE p.type_de_personne = 'PERSONNE_MORALE' AND p.actif = true AND p.entreprise_siren IS NOT NULL
        ) AS parent_sirens_raw,
        array_agg(DISTINCT p.entreprise_denomination) FILTER (
            WHERE p.type_de_personne = 'PERSONNE_MORALE' AND p.actif = true AND p.entreprise_denomination IS NOT NULL
        ) AS parent_denominations
    FROM bronze.inpi_formalites_personnes p
    WHERE p.siren IN (SELECT siren FROM sci_base)
    GROUP BY p.siren
),

-- ───────── 4. DIRIGEANTS INDIVIDUS via reverse-lookup silver.inpi_dirigeants ─────────
-- Top 5 par n_mandats_actifs (le plus actif d'abord).
dirigeants_aggr AS (
    SELECT
        sb.siren,
        array_agg(DISTINCT (d.prenom || ' ' || d.nom) ORDER BY (d.prenom || ' ' || d.nom)) AS dirigeants_noms_all,
        array_agg(DISTINCT d.age_2026 ORDER BY d.age_2026 DESC NULLS LAST) AS dirigeants_ages_all,
        max(d.age_2026) AS age_dirigeant_max,
        min(d.age_2026) AS age_dirigeant_min,
        bool_or(d.age_2026 >= 60) AS has_dirigeant_senior,
        bool_or(d.age_2026 < 18) AS has_minor_dirigeant,
        -- has_successeur : proxy "présence d'un dirigeant < 45 ans" (transmission).
        -- On ne peut pas combiner mode() WITHIN GROUP avec OVER (PARTITION) en
        -- Postgres ; le proxy plus simple est suffisant pour l'usage M&A.
        bool_or(d.age_2026 < 45) AS has_successeur,
        count(DISTINCT d.nom) AS n_distinct_noms_famille
    FROM sci_base sb
    JOIN silver.inpi_dirigeants d ON sb.siren::char(9) = ANY(d.sirens_mandats)
    GROUP BY sb.siren
),

-- famille_dominante_nom = nom le plus fréquent
famille_dom AS (
    SELECT
        sb.siren,
        d.nom AS famille_dominante_nom,
        count(*) AS cnt,
        ROW_NUMBER() OVER (PARTITION BY sb.siren ORDER BY count(*) DESC, d.nom) AS rn
    FROM sci_base sb
    JOIN silver.inpi_dirigeants d ON sb.siren::char(9) = ANY(d.sirens_mandats)
    GROUP BY sb.siren, d.nom
),

-- ───────── 5. DVF ZONE par code postal ─────────
dvf_zone AS (
    SELECT
        code_postal,
        count(*) AS dvf_zone_n_transactions_5y,
        percentile_cont(0.5) WITHIN GROUP (
            ORDER BY valeur_fonciere / NULLIF(surface_reelle_bati, 0)
        ) FILTER (
            WHERE surface_reelle_bati > 10
              AND valeur_fonciere > 50000
              AND surface_reelle_bati < 1000
        ) AS dvf_zone_prix_m2_median,
        percentile_cont(0.25) WITHIN GROUP (
            ORDER BY valeur_fonciere / NULLIF(surface_reelle_bati, 0)
        ) FILTER (
            WHERE surface_reelle_bati > 10
              AND valeur_fonciere > 50000
              AND surface_reelle_bati < 1000
        ) AS dvf_zone_prix_m2_p25,
        percentile_cont(0.75) WITHIN GROUP (
            ORDER BY valeur_fonciere / NULLIF(surface_reelle_bati, 0)
        ) FILTER (
            WHERE surface_reelle_bati > 10
              AND valeur_fonciere > 50000
              AND surface_reelle_bati < 1000
        ) AS dvf_zone_prix_m2_p75,
        sum(valeur_fonciere) AS dvf_zone_total_volume_eur
    FROM silver.dvf_transactions
    WHERE date_mutation >= now() - interval '5 years'
      AND code_postal IS NOT NULL
      AND code_postal IN (
          SELECT DISTINCT adresse_code_postal::text
          FROM sci_base
          WHERE adresse_code_postal IS NOT NULL
      )
    GROUP BY code_postal
)

-- ───────── ASSEMBLY FINAL ─────────
SELECT
    -- LAYER 1 — IDENTITÉ
    s.siren,
    s.denomination,
    s.forme_juridique,
    s.code_ape,
    s.sigle,
    s.nom_commercial,
    s.is_sci,
    s.is_holding_patrimoniale,

    -- LAYER 2 — ADRESSE
    s.adresse_voie,
    s.adresse_code_postal,
    s.adresse_dept,
    s.adresse_pays,
    s.date_immatriculation,
    s.age_entreprise,

    -- LAYER 3 — PATRIMOINE FINANCIER
    s.capital_social,
    lb.total_actif,
    lb.immo_corporelles,
    GREATEST(
        COALESCE(lb.total_actif, 0) - COALESCE(lb.immo_corporelles, 0),
        0
    ) AS immo_financieres,
    COALESCE(lb.immo_corporelles, 0) AS immo_total,
    lb.capitaux_propres,
    lb.emprunts_dettes,
    -- ⭐ KPI : patrimoine net estimé
    CASE
        WHEN lb.total_actif IS NOT NULL THEN COALESCE(lb.total_actif, 0) - COALESCE(lb.emprunts_dettes, 0)
        WHEN lb.immo_corporelles IS NOT NULL THEN lb.immo_corporelles
        ELSE NULL
    END AS patrimoine_net_estime,
    lb.ca_net,
    lb.resultat_net,
    lb.effectif_moyen,
    lb.date_cloture AS date_cloture_dernier_bilan,
    (lb.date_cloture >= (now() - interval '2 years')::date) AS has_bilan_recent,

    -- LAYER 4 — OWNERSHIP
    COALESCE(o.n_dirigeants_individu, 0) AS n_dirigeants_individu,
    COALESCE(o.n_dirigeants_morale, 0) AS n_dirigeants_morale,
    CASE
        WHEN COALESCE(o.n_dirigeants_morale, 0) = 0 AND COALESCE(o.n_dirigeants_individu, 0) > 0 THEN 'individual'
        WHEN COALESCE(o.n_dirigeants_individu, 0) = 0 AND COALESCE(o.n_dirigeants_morale, 0) > 0 THEN 'corporate'
        WHEN COALESCE(o.n_dirigeants_individu, 0) > 0 AND COALESCE(o.n_dirigeants_morale, 0) > 0 THEN 'mixed'
        ELSE 'unknown'
    END AS ownership_type,

    -- LAYER 5 — DIRIGEANTS INDIVIDUS (top 5)
    da.dirigeants_noms_all[1:5] AS dirigeants_individus_noms,
    da.dirigeants_ages_all[1:5] AS dirigeants_individus_ages,
    da.age_dirigeant_max,
    da.age_dirigeant_min,
    COALESCE(da.has_dirigeant_senior, false) AS has_dirigeant_senior,
    COALESCE(da.has_minor_dirigeant, false) AS has_minor_dirigeant,
    COALESCE(da.has_successeur, false) AS has_successeur,
    (COALESCE(da.n_distinct_noms_famille, 0) = 1) AS has_famille_unique,
    fd.famille_dominante_nom,

    -- LAYER 6 — PARENTS CORPORATE
    o.parent_sirens_raw AS parent_sirens,
    o.parent_denominations,

    -- LAYER 7 — DVF ZONE
    dvf.dvf_zone_n_transactions_5y,
    dvf.dvf_zone_prix_m2_median,
    dvf.dvf_zone_prix_m2_p25,
    dvf.dvf_zone_prix_m2_p75,
    dvf.dvf_zone_total_volume_eur,
    -- Estimations valuation immo (3 niveaux)
    lb.immo_corporelles AS estimation_value_min_eur,
    (COALESCE(lb.immo_corporelles, 0) + COALESCE(lb.total_actif, 0) - COALESCE(lb.emprunts_dettes, 0)) / 2.0 AS estimation_value_avg_eur,
    lb.total_actif AS estimation_value_max_eur,

    -- METADATA
    now() AS materialized_at

FROM sci_base s
LEFT JOIN last_bilan lb ON lb.siren = s.siren
LEFT JOIN ownership o ON o.siren = s.siren
LEFT JOIN dirigeants_aggr da ON da.siren = s.siren
LEFT JOIN famille_dom fd ON fd.siren = s.siren AND fd.rn = 1
LEFT JOIN dvf_zone dvf ON dvf.code_postal = s.adresse_code_postal::text
;

-- Indexes principaux
CREATE UNIQUE INDEX sci_master_siren_idx ON silver.sci_master (siren);
CREATE INDEX sci_master_patrimoine_net_idx ON silver.sci_master (patrimoine_net_estime DESC NULLS LAST);
CREATE INDEX sci_master_ownership_type_idx ON silver.sci_master (ownership_type);
CREATE INDEX sci_master_adresse_dept_idx ON silver.sci_master (adresse_dept);
CREATE INDEX sci_master_is_sci_idx ON silver.sci_master (is_sci) WHERE is_sci = true;
CREATE INDEX sci_master_has_bilan_recent_idx ON silver.sci_master (has_bilan_recent) WHERE has_bilan_recent = true;
