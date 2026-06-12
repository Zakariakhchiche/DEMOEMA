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
    NOW() AS materialized_at
FROM base b;

CREATE INDEX ON gold.scoring_ma (siren);
CREATE INDEX ON gold.scoring_ma (score_total DESC);
CREATE INDEX ON gold.scoring_ma (tier);
CREATE INDEX ON gold.scoring_ma (code_ape);
CREATE INDEX ON gold.scoring_ma (adresse_dept);
CREATE INDEX ON gold.scoring_ma (ca_latest DESC NULLS LAST);
CREATE INDEX ON gold.scoring_ma (age_dirigeant_max DESC NULLS LAST);

