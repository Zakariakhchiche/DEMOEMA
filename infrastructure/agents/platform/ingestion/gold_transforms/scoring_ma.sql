SET statement_timeout = 0;
DROP TABLE IF EXISTS gold.scoring_ma CASCADE;

CREATE TABLE gold.scoring_ma AS
WITH base AS (
    SELECT
        em.siren,
        em.denomination,
        em.code_ape,
        em.adresse_dept,
        em.adresse_commune,
        em.forme_juridique,
        em.capital_social,
        em.age_entreprise,
        em.effectif_salarie,
        em.ca_latest,
        em.capitaux_propres_latest,
        em.resultat_net_latest,
        em.has_bilan_recent,
        em.effectif_moyen_latest,
        em.age_dirigeant_max,
        em.has_dirigeant_senior,
        em.n_sci_dirigeants,
        em.total_capital_sci,
        em.has_holding_patrimoniale,
        em.n_mandats_dirigeant_max,
        em.has_pro_ma,
        em.n_dirigeants,
        em.has_late_filing,
        em.lei,
        em.insee_etat_administratif,
        em.pro_ma_score AS base_pro_ma_score
    FROM gold.entreprises_master em
)
SELECT
    b.siren,
    b.denomination,
    b.code_ape,
    b.adresse_dept,
    b.adresse_commune,
    b.forme_juridique,
    b.capital_social,
    b.age_entreprise,
    b.effectif_salarie,
    b.ca_latest,
    b.capitaux_propres_latest,
    b.resultat_net_latest,
    b.effectif_moyen_latest,
    b.age_dirigeant_max,
    b.has_dirigeant_senior,
    b.n_sci_dirigeants,
    b.total_capital_sci,
    b.has_holding_patrimoniale,
    b.n_mandats_dirigeant_max,
    b.has_pro_ma,
    b.n_dirigeants,
    b.has_bilan_recent,
    b.has_late_filing,
    b.lei,
    -- Dimension 1 : Maturité dirigeant (20pts)
    LEAST(20,
        (CASE WHEN b.age_dirigeant_max >= 70 THEN 20
              WHEN b.age_dirigeant_max >= 65 THEN 15
              WHEN b.age_dirigeant_max >= 60 THEN 10
              ELSE 0 END)
    )::int AS dim1_maturite_score,
    -- Dimension 2 : Patrimoine SCI (20pts)
    LEAST(20,
        (CASE WHEN b.n_sci_dirigeants >= 3 THEN 20
              WHEN b.n_sci_dirigeants >= 2 THEN 15
              WHEN b.n_sci_dirigeants = 1 THEN 5
              ELSE 0 END)
    )::int AS dim2_patrimoine_score,
    -- Dimension 3 : Financier (15pts)
    LEAST(15,
        (CASE WHEN b.has_bilan_recent THEN 5 ELSE 0 END)
        + (LEAST(10, GREATEST(0, COALESCE(b.ca_latest, 0) / 10000000.0)))::int
    )::int AS dim3_financier_score,
    -- Dimension 4 : Multi-mandats dirigeants (10pts)
    LEAST(10,
        (CASE WHEN b.n_mandats_dirigeant_max >= 10 THEN 10
              WHEN b.n_mandats_dirigeant_max >= 5 THEN 7
              WHEN b.n_mandats_dirigeant_max >= 3 THEN 3
              ELSE 0 END)
    )::int AS dim4_mandats_score,
    -- Dimension 5 : Légal/Compliance (-10pts négatif)
    (CASE WHEN b.has_late_filing THEN -10 ELSE 0 END)::int AS dim5_compliance_pen,
    -- Score composite final 0-100
    GREATEST(0, LEAST(100,
        50  -- baseline
        + (CASE WHEN b.age_dirigeant_max >= 70 THEN 20
              WHEN b.age_dirigeant_max >= 65 THEN 15
              WHEN b.age_dirigeant_max >= 60 THEN 10 ELSE 0 END)
        + (CASE WHEN b.n_sci_dirigeants >= 3 THEN 20
              WHEN b.n_sci_dirigeants >= 2 THEN 15
              WHEN b.n_sci_dirigeants = 1 THEN 5 ELSE 0 END)
        + (CASE WHEN b.has_bilan_recent THEN 5 ELSE 0 END)
        + (LEAST(10, GREATEST(0, COALESCE(b.ca_latest, 0) / 10000000.0)))::int
        + (CASE WHEN b.n_mandats_dirigeant_max >= 10 THEN 10
              WHEN b.n_mandats_dirigeant_max >= 5 THEN 7
              WHEN b.n_mandats_dirigeant_max >= 3 THEN 3 ELSE 0 END)
        + (CASE WHEN b.has_pro_ma THEN 5 ELSE 0 END)
        + (CASE WHEN b.has_holding_patrimoniale THEN 5 ELSE 0 END)
        - (CASE WHEN b.has_late_filing THEN 10 ELSE 0 END)
        - (CASE WHEN COALESCE(b.resultat_net_latest, 0) < 0 THEN 5 ELSE 0 END)
        - (CASE WHEN b.insee_etat_administratif = $$F$$ THEN 50 ELSE 0 END)
    ))::int AS score_total,
    -- Tier qualifie
    CASE
        WHEN GREATEST(0, LEAST(100,
            50
            + (CASE WHEN b.age_dirigeant_max >= 70 THEN 20
                  WHEN b.age_dirigeant_max >= 65 THEN 15
                  WHEN b.age_dirigeant_max >= 60 THEN 10 ELSE 0 END)
            + (CASE WHEN b.n_sci_dirigeants >= 2 THEN 15 ELSE 0 END)
            + (CASE WHEN b.has_bilan_recent THEN 5 ELSE 0 END)
            + (LEAST(10, GREATEST(0, COALESCE(b.ca_latest, 0) / 10000000.0)))::int
        )) >= 80 THEN $$A_HOT$$
        WHEN GREATEST(0, LEAST(100,
            50
            + (CASE WHEN b.age_dirigeant_max >= 65 THEN 15 ELSE 0 END)
            + (CASE WHEN b.has_bilan_recent THEN 5 ELSE 0 END)
        )) >= 65 THEN $$B_WARM$$
        ELSE $$C_COLD$$
    END AS tier,
    -- ─── 4 AXES v3 (0-100) affichés dans la fiche ─────────────────────────────
    -- TRANSMISSION : probabilité de cession (âge dirigeant + patrimoine optimisé)
    LEAST(100, GREATEST(0,
        (CASE WHEN b.age_dirigeant_max >= 70 THEN 50
              WHEN b.age_dirigeant_max >= 65 THEN 40
              WHEN b.age_dirigeant_max >= 60 THEN 30
              WHEN b.age_dirigeant_max >= 55 THEN 15 ELSE 0 END)
        + (CASE WHEN b.n_sci_dirigeants >= 3 THEN 30
                WHEN b.n_sci_dirigeants >= 2 THEN 20
                WHEN b.n_sci_dirigeants = 1 THEN 10 ELSE 0 END)
        + (CASE WHEN b.has_holding_patrimoniale THEN 20 ELSE 0 END)
    ))::int AS transmission_score,
    -- ATTRACTIVITY : valeur réelle (marge EBITDA + rentabilité + solidité)
    LEAST(100, GREATEST(0,
        (CASE WHEN es.ebitda_margin >= 0.15 THEN 50
              WHEN es.ebitda_margin >= 0.08 THEN 35
              WHEN es.ebitda_margin >= 0.03 THEN 20
              WHEN es.ebitda_margin > 0     THEN 10 ELSE 0 END)
        + (CASE WHEN COALESCE(b.resultat_net_latest, 0) > 0 THEN 25 ELSE 0 END)
        + (CASE WHEN COALESCE(es.has_negative_equity, false) = false THEN 15 ELSE 0 END)
        + (CASE WHEN b.has_bilan_recent THEN 10 ELSE 0 END)
    ))::int AS attractivity_score,
    -- SCALE : barrière transactionnelle (CA absolu)
    (CASE WHEN b.ca_latest >= 100000000 THEN 100
          WHEN b.ca_latest >= 50000000  THEN 85
          WHEN b.ca_latest >= 20000000  THEN 70
          WHEN b.ca_latest >= 10000000  THEN 55
          WHEN b.ca_latest >= 5000000   THEN 40
          WHEN b.ca_latest >= 2000000   THEN 25
          WHEN b.ca_latest > 0          THEN 10 ELSE 0 END)::int AS scale_score,
    -- STRUCTURE : suitability (multi-mandats + holding + capital)
    LEAST(100, GREATEST(0,
        30
        + (CASE WHEN b.n_mandats_dirigeant_max >= 5 THEN 30
                WHEN b.n_mandats_dirigeant_max >= 3 THEN 20
                WHEN b.n_mandats_dirigeant_max >= 1 THEN 10 ELSE 0 END)
        + (CASE WHEN b.has_holding_patrimoniale THEN 20 ELSE 0 END)
        + (CASE WHEN COALESCE(b.capital_social, 0) >= 1000000 THEN 20
                WHEN COALESCE(b.capital_social, 0) >= 250000 THEN 10 ELSE 0 END)
    ))::int AS structure_score,
    -- ─── Ratios financiers (passthrough depuis le feature store, grille Orascom) ───
    es.proxy_ebitda,
    es.ebitda_margin,
    es.ebit_margin,
    es.net_margin,
    es.ebitda_on_assets,
    es.debt_to_ebitda,
    es.debt_to_equity,
    es.debt_ratio,
    es.equity_ratio,
    es.dso_days,
    es.revenue_volatility,
    es.revenue_growth_yoy,
    es.financial_health_tier,
    COALESCE(es.has_negative_equity, false)  AS has_negative_equity,
    COALESCE(es.has_negative_ebitda, false)  AS has_negative_ebitda,
    COALESCE(es.has_high_leverage, false)    AS has_high_leverage,
    COALESCE(es.has_revenue_decline, false)  AS has_revenue_decline,
    NOW() AS materialized_at
FROM base b
LEFT JOIN silver.entreprises_signals es ON es.siren = b.siren;

CREATE INDEX ON gold.scoring_ma (siren);
CREATE INDEX ON gold.scoring_ma (score_total DESC);
CREATE INDEX ON gold.scoring_ma (tier);
CREATE INDEX ON gold.scoring_ma (code_ape);
CREATE INDEX ON gold.scoring_ma (adresse_dept);
CREATE INDEX ON gold.scoring_ma (ca_latest DESC NULLS LAST);
CREATE INDEX ON gold.scoring_ma (age_dirigeant_max DESC NULLS LAST);

