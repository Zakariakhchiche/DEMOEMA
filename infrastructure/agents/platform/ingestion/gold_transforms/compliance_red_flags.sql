-- gold.compliance_red_flags — SQL ÉCRIT À LA MAIN (déterministe, sans LLM).
-- Versionné dans git ; appliqué via gold_engine (gold_transforms).
--
-- Red flags compliance / DD M&A consolidés, 1 row par siren cible (depuis
-- gold.entreprises_master, ~411k cibles SAS/SA capital>=100k€). Ne dépend PAS de
-- silver.gels_avoirs (stub). Réécriture 2026-06-12 : compliance COMPLÈTE —
-- ajoute offshore (icij), procédures collectives (BODACC) et les drapeaux de
-- détresse financière issus des ratios de silver.entreprises_signals.
--
-- Sources : gold.entreprises_master, silver.opensanctions, silver.cnil_sanctions,
-- silver.dgccrf_sanctions, silver.icij_offshore_match, silver.bodacc_annonces,
-- silver.entreprises_signals (ratios / détresse).

SET statement_timeout = 0;
DROP TABLE IF EXISTS gold.compliance_red_flags CASCADE;

CREATE TABLE gold.compliance_red_flags AS
WITH offshore AS (
    SELECT DISTINCT btrim(m.siren) AS siren
    FROM silver.icij_offshore_match icij
    CROSS JOIN LATERAL unnest(icij.sirens_mandats) AS m(siren)
),
procedures AS (
    SELECT DISTINCT siren
    FROM silver.bodacc_annonces
    WHERE (familleavis_lib ILIKE '%redress%'
        OR familleavis_lib ILIKE '%liquid%'
        OR familleavis_lib ILIKE '%proc%coll%')
      AND date_parution > now() - interval '24 months'
),
sanctions AS (
    SELECT DISTINCT s AS siren
    FROM silver.opensanctions os
    CROSS JOIN LATERAL unnest(os.sirens_fr) AS s
)
SELECT
    em.siren,
    em.denomination,
    em.code_ape,
    em.adresse_dept,
    em.insee_etat_administratif,
    -- ─── Flags légaux / sanctions ───
    (em.insee_etat_administratif = 'F')              AS is_radiation,
    COALESCE(em.has_late_filing, false)              AS has_late_filing,
    (sa.siren IS NOT NULL)                           AS has_sanction,
    EXISTS(SELECT 1 FROM silver.cnil_sanctions cs   WHERE cs.payload->>'siren' = em.siren) AS has_cnil_sanction,
    EXISTS(SELECT 1 FROM silver.dgccrf_sanctions ds WHERE ds.payload->>'siren' = em.siren) AS has_dgccrf_sanction,
    (o.siren IS NOT NULL)                            AS has_offshore_link,
    (p.siren IS NOT NULL)                            AS has_procedure_collective,
    -- ─── Détresse financière (ratios silver.entreprises_signals) ───
    COALESCE(es.has_negative_equity, false)          AS has_negative_equity,
    COALESCE(es.has_negative_ebitda, false)          AS has_negative_ebitda,
    COALESCE(es.has_high_leverage, false)            AS has_high_leverage,
    COALESCE(es.has_revenue_decline, false)          AS has_revenue_decline,
    es.debt_to_ebitda,
    es.financial_health_tier,
    -- ─── Risk score agrégé 0-100 ───
    LEAST(100, (
          (CASE WHEN em.insee_etat_administratif = 'F'        THEN 40 ELSE 0 END)
        + (CASE WHEN p.siren IS NOT NULL                       THEN 40 ELSE 0 END)
        + (CASE WHEN sa.siren IS NOT NULL                      THEN 40 ELSE 0 END)
        + (CASE WHEN o.siren IS NOT NULL                       THEN 25 ELSE 0 END)
        + (CASE WHEN COALESCE(es.has_negative_equity, false)   THEN 20 ELSE 0 END)
        + (CASE WHEN COALESCE(es.has_high_leverage, false)     THEN 15 ELSE 0 END)
        + (CASE WHEN COALESCE(es.has_negative_ebitda, false)   THEN 10 ELSE 0 END)
        + (CASE WHEN COALESCE(em.has_late_filing, false)       THEN 10 ELSE 0 END)
        + (CASE WHEN COALESCE(es.has_revenue_decline, false)   THEN  5 ELSE 0 END)
    ))::int AS risk_score,
    -- ─── Sévérité max (CRITICAL = élimine, HIGH/MEDIUM = qualifie) ───
    CASE
        WHEN em.insee_etat_administratif = 'F'
             OR p.siren IS NOT NULL
             OR sa.siren IS NOT NULL                          THEN 'CRITICAL'
        WHEN o.siren IS NOT NULL
             OR COALESCE(es.has_negative_equity, false)
             OR COALESCE(es.has_high_leverage, false)         THEN 'HIGH'
        WHEN COALESCE(em.has_late_filing, false)
             OR COALESCE(es.has_negative_ebitda, false)
             OR COALESCE(es.has_revenue_decline, false)       THEN 'MEDIUM'
        ELSE 'NONE'
    END AS flag_severity_max,
    now() AS materialized_at
FROM gold.entreprises_master em
LEFT JOIN silver.entreprises_signals es ON es.siren = em.siren
LEFT JOIN offshore o   ON o.siren = em.siren
LEFT JOIN procedures p ON p.siren = em.siren
LEFT JOIN sanctions sa ON sa.siren = em.siren;

CREATE INDEX compliance_red_flags_siren_idx        ON gold.compliance_red_flags (siren);
CREATE INDEX compliance_red_flags_risk_idx         ON gold.compliance_red_flags (risk_score DESC);
CREATE INDEX compliance_red_flags_severity_idx     ON gold.compliance_red_flags (flag_severity_max);
CREATE INDEX compliance_red_flags_radiation_idx    ON gold.compliance_red_flags (is_radiation) WHERE is_radiation = true;
CREATE INDEX compliance_red_flags_sanction_idx     ON gold.compliance_red_flags (has_sanction) WHERE has_sanction = true;
CREATE INDEX compliance_red_flags_proc_idx         ON gold.compliance_red_flags (has_procedure_collective) WHERE has_procedure_collective = true;
CREATE INDEX compliance_red_flags_neg_equity_idx   ON gold.compliance_red_flags (has_negative_equity) WHERE has_negative_equity = true;
