-- gold.scoring_ma v3 PRO OPTIMIZED — barème advisor M&A small/mid cap
-- 4 axes business + 1 axe risk, formule géométrique, percentile-based tier
-- VERSION OPT : pré-aggregations CTE en lieu de EXISTS sub-queries
SET statement_timeout = 0;
DROP TABLE IF EXISTS gold.scoring_ma CASCADE;

-- Pré-agrégations sanctions / bodacc / cession en une seule passe
CREATE TEMP TABLE _sanctions_idx AS
SELECT DISTINCT s.siren_unnest AS siren, true AS has_ofac_eu
FROM (
    SELECT unnest(sirens_fr) AS siren_unnest
    FROM silver.opensanctions
    WHERE sirens_fr IS NOT NULL AND array_length(sirens_fr, 1) > 0
) s;
CREATE INDEX ON _sanctions_idx (siren);

CREATE TEMP TABLE _cnil_idx AS
SELECT DISTINCT (payload->>'siren')::char(9) AS siren
FROM silver.cnil_sanctions
WHERE payload->>'siren' IS NOT NULL;
CREATE INDEX ON _cnil_idx (siren);

CREATE TEMP TABLE _dgccrf_idx AS
SELECT DISTINCT (payload->>'siren')::char(9) AS siren
FROM silver.dgccrf_sanctions
WHERE payload->>'siren' IS NOT NULL;
CREATE INDEX ON _dgccrf_idx (siren);

CREATE TEMP TABLE _bodacc_proc_idx AS
SELECT DISTINCT siren
FROM silver.bodacc_annonces
WHERE siren IS NOT NULL
  AND date_parution > now()::date - interval '24 months'
  AND (familleavis_lib ILIKE '%procedure%'
       OR familleavis_lib ILIKE '%redressement%'
       OR familleavis_lib ILIKE '%liquidation%'
       OR familleavis_lib ILIKE '%sauvegarde%');
CREATE INDEX ON _bodacc_proc_idx (siren);

CREATE TEMP TABLE _cession_idx AS
SELECT DISTINCT siren
FROM silver.cession_events
WHERE siren IS NOT NULL AND is_recent = true;
CREATE INDEX ON _cession_idx (siren);

-- Construction principale via JOINS rapides
CREATE TABLE gold.scoring_ma AS
WITH proxy AS (
    SELECT
        em.*,
        COALESCE(em.resultat_net_latest, 0) + COALESCE(em.capital_social * 0.05, 0) AS proxy_ebitda,
        CASE
            WHEN em.ca_latest IS NULL OR em.ca_latest = 0 THEN NULL
            ELSE (COALESCE(em.resultat_net_latest, 0) + COALESCE(em.capital_social * 0.05, 0)) / em.ca_latest
        END AS proxy_margin,
        CASE
            WHEN em.code_ape ~ '^(62|63)\.' THEN 8.5
            WHEN em.code_ape ~ '^86\.'      THEN 9.5
            WHEN em.code_ape ~ '^(30|32\.50)' THEN 7.0
            WHEN em.code_ape ~ '^(70|71)\.' THEN 6.0
            WHEN em.code_ape ~ '^(25|28)\.' THEN 5.5
            WHEN em.code_ape ~ '^(41|42|43)\.' THEN 4.5
            WHEN em.code_ape ~ '^(47|56)\.' THEN 3.5
            WHEN em.code_ape ~ '^(52|53)\.' THEN 4.0
            WHEN em.code_ape ~ '^58\.'      THEN 7.5
            WHEN em.code_ape ~ '^(64|65|66)\.' THEN 5.0
            ELSE 5.0
        END AS sector_multiple,
        (em.code_ape ~ '^(62|63|86|71|70|30|58)\.') AS is_sector_premium,
        (em.adresse_dept IN ('75','92','78','94','93','77','95','91','69','13','06','33','31','35','59','67','44','38')) AS is_geo_premium,
        (em.n_exercices_deposes >= 3 AND em.age_entreprise >= 5) AS is_stable,
        (em.effectif_salarie >= 11) AS is_multi_etab,
        (em.forme_juridique IN ('5710','5720','5730','5485','5499','5505','5510','5515','5520','5530','5540','5599')) AS is_clean_legal_form
    FROM gold.entreprises_master em
),
scored AS (
    SELECT
        p.*,
        (sa.siren IS NOT NULL) AS has_sanction_ofac_eu,
        (cn.siren IS NOT NULL) AS has_sanction_cnil,
        (dg.siren IS NOT NULL) AS has_sanction_dgccrf,
        (bp.siren IS NOT NULL) AS has_proc_collective_recent,
        (ce.siren IS NOT NULL) AS has_cession_recent,
        0::int AS n_contentieux_recent,

        LEAST(100, GREATEST(0,
            CASE
                WHEN p.age_dirigeant_max IS NULL THEN 0
                WHEN p.age_dirigeant_max < 55 THEN 0
                WHEN p.age_dirigeant_max >= 75 THEN 90
                ELSE ((p.age_dirigeant_max - 55) * 4.5)::int
            END
            + CASE
                WHEN p.n_sci_dirigeants >= 2 AND p.total_capital_sci > 500000 THEN 30
                WHEN p.n_sci_dirigeants >= 2 THEN 20
                WHEN p.n_sci_dirigeants = 1 THEN 8
                ELSE 0
              END
            + CASE WHEN p.has_late_filing THEN 12 ELSE 0 END
            + CASE WHEN p.n_dirigeants = 1 AND p.age_dirigeant_max >= 60 THEN 8 ELSE 0 END
        ))::int AS transmission_score,

        LEAST(100, GREATEST(0,
            CASE
                WHEN p.proxy_margin IS NULL THEN 0
                WHEN p.proxy_margin >= 0.20 THEN 50
                WHEN p.proxy_margin >= 0.15 THEN 40
                WHEN p.proxy_margin >= 0.10 THEN 30
                WHEN p.proxy_margin >= 0.05 THEN 15
                WHEN p.proxy_margin >= 0   THEN 5
                ELSE 0
            END
            + CASE WHEN p.is_stable THEN 15 ELSE 0 END
            + CASE WHEN p.is_sector_premium THEN 15 ELSE 0 END
            + CASE WHEN p.is_geo_premium THEN 10 ELSE 0 END
            + CASE
                WHEN COALESCE(p.capitaux_propres_latest, 0) > p.capital_social * 2 THEN 10
                WHEN COALESCE(p.capitaux_propres_latest, 0) > 0 THEN 5
                ELSE 0
              END
        ))::int AS attractivity_score,

        LEAST(100, GREATEST(0,
            CASE
                WHEN p.ca_latest IS NULL THEN 0
                WHEN p.ca_latest >= 100000000 THEN 100
                WHEN p.ca_latest >= 50000000 THEN 85
                WHEN p.ca_latest >= 20000000 THEN 70
                WHEN p.ca_latest >= 10000000 THEN 55
                WHEN p.ca_latest >= 5000000 THEN 35
                WHEN p.ca_latest >= 2000000 THEN 15
                ELSE 0
            END
            + CASE WHEN p.is_multi_etab THEN 5 ELSE 0 END
            + CASE WHEN p.lei IS NOT NULL THEN 5 ELSE 0 END
        ))::int AS scale_score,

        LEAST(100, GREATEST(0,
            CASE WHEN p.is_clean_legal_form THEN 40 ELSE 10 END
            + CASE WHEN p.has_pro_ma THEN 25 ELSE 0 END
            + CASE WHEN p.n_mandats_dirigeant_max >= 5 THEN 15 ELSE 0 END
            + CASE WHEN p.has_holding_patrimoniale THEN 20 ELSE 0 END
        ))::int AS structure_score,

        CASE
            WHEN sa.siren IS NOT NULL THEN 0
            WHEN p.insee_etat_administratif = 'F' THEN 0
            WHEN bp.siren IS NOT NULL THEN 0
            ELSE 1.0
                * (CASE WHEN cn.siren IS NOT NULL THEN 0.75 ELSE 1.0 END)
                * (CASE WHEN dg.siren IS NOT NULL THEN 0.80 ELSE 1.0 END)
                * (CASE WHEN p.has_late_filing THEN 0.90 ELSE 1.0 END)
                * (CASE WHEN COALESCE(p.resultat_net_latest, 0) < 0 THEN 0.90 ELSE 1.0 END)
        END AS risk_multiplier
    FROM proxy p
    LEFT JOIN _sanctions_idx sa ON sa.siren = p.siren
    LEFT JOIN _cnil_idx cn ON cn.siren = p.siren
    LEFT JOIN _dgccrf_idx dg ON dg.siren = p.siren
    LEFT JOIN _bodacc_proc_idx bp ON bp.siren = p.siren
    LEFT JOIN _cession_idx ce ON ce.siren = p.siren
),
scored_with_composite AS (
    SELECT
        s.*,
        (POWER(GREATEST(s.transmission_score, 1) * GREATEST(s.attractivity_score, 1) * GREATEST(s.scale_score, 1), 1.0/3.0) * s.risk_multiplier)::int AS deal_score_raw,
        CASE
            WHEN s.proxy_ebitda > 0 THEN
                (s.proxy_ebitda * s.sector_multiple
                 * (CASE WHEN s.ca_latest >= 50000000 THEN 1.4
                         WHEN s.ca_latest >= 10000000 THEN 1.2
                         ELSE 1.0 END))::numeric(20,0)
            ELSE NULL
        END AS ev_estimated_eur
    FROM scored s
),
ranked AS (
    SELECT
        sc.*,
        ntile(100) OVER (ORDER BY sc.deal_score_raw DESC) AS deal_percentile
    FROM scored_with_composite sc
    WHERE sc.risk_multiplier > 0
)
SELECT
    r.siren, r.denomination, r.code_ape, r.adresse_dept, r.adresse_commune,
    r.forme_juridique, r.capital_social, r.age_entreprise, r.effectif_salarie,
    r.ca_latest, r.capitaux_propres_latest, r.resultat_net_latest,
    r.proxy_ebitda, r.proxy_margin, r.sector_multiple,
    r.is_sector_premium, r.is_geo_premium, r.is_stable, r.is_multi_etab, r.is_clean_legal_form,
    r.age_dirigeant_max, r.has_dirigeant_senior,
    r.n_dirigeants, r.n_mandats_dirigeant_max, r.has_pro_ma,
    r.n_sci_dirigeants, r.total_capital_sci, r.has_holding_patrimoniale,
    r.has_bilan_recent, r.has_late_filing, r.lei, r.insee_etat_administratif,
    r.transmission_score, r.attractivity_score, r.scale_score, r.structure_score,
    r.has_sanction_ofac_eu, r.has_sanction_cnil, r.has_sanction_dgccrf,
    r.has_proc_collective_recent, r.has_cession_recent, r.n_contentieux_recent,
    r.risk_multiplier::numeric(4,3) AS risk_multiplier,
    r.deal_score_raw,
    r.ev_estimated_eur,
    r.deal_percentile,
    CASE
        WHEN r.deal_percentile <= 1 THEN 'A_HOT'
        WHEN r.deal_percentile <= 5 THEN 'B_WARM'
        WHEN r.deal_percentile <= 20 THEN 'C_PIPELINE'
        WHEN r.deal_percentile <= 50 THEN 'D_WATCH'
        ELSE 'E_REJECT'
    END AS tier,
    r.deal_score_raw AS score_total,
    NOW() AS materialized_at
FROM ranked r
UNION ALL
SELECT
    s.siren, s.denomination, s.code_ape, s.adresse_dept, s.adresse_commune,
    s.forme_juridique, s.capital_social, s.age_entreprise, s.effectif_salarie,
    s.ca_latest, s.capitaux_propres_latest, s.resultat_net_latest,
    s.proxy_ebitda, s.proxy_margin, s.sector_multiple,
    s.is_sector_premium, s.is_geo_premium, s.is_stable, s.is_multi_etab, s.is_clean_legal_form,
    s.age_dirigeant_max, s.has_dirigeant_senior,
    s.n_dirigeants, s.n_mandats_dirigeant_max, s.has_pro_ma,
    s.n_sci_dirigeants, s.total_capital_sci, s.has_holding_patrimoniale,
    s.has_bilan_recent, s.has_late_filing, s.lei, s.insee_etat_administratif,
    s.transmission_score, s.attractivity_score, s.scale_score, s.structure_score,
    s.has_sanction_ofac_eu, s.has_sanction_cnil, s.has_sanction_dgccrf,
    s.has_proc_collective_recent, s.has_cession_recent, s.n_contentieux_recent,
    s.risk_multiplier::numeric(4,3),
    s.deal_score_raw,
    s.ev_estimated_eur,
    NULL::int AS deal_percentile,
    'Z_ELIM' AS tier,
    0 AS score_total,
    NOW() AS materialized_at
FROM scored_with_composite s
WHERE s.risk_multiplier = 0;

CREATE INDEX ON gold.scoring_ma (siren);
CREATE INDEX ON gold.scoring_ma (deal_score_raw DESC);
CREATE INDEX ON gold.scoring_ma (tier);
CREATE INDEX ON gold.scoring_ma (deal_percentile);
CREATE INDEX ON gold.scoring_ma (transmission_score DESC);
CREATE INDEX ON gold.scoring_ma (attractivity_score DESC);
CREATE INDEX ON gold.scoring_ma (scale_score DESC);
CREATE INDEX ON gold.scoring_ma (ev_estimated_eur DESC NULLS LAST);
CREATE INDEX ON gold.scoring_ma (code_ape);
CREATE INDEX ON gold.scoring_ma (adresse_dept);
