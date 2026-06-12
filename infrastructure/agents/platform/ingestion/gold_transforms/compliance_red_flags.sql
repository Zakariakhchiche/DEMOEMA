SET statement_timeout = 0;
DROP TABLE IF EXISTS gold.compliance_red_flags CASCADE;

-- silver.gels_avoirs nexiste pas → on stub avec NULL/false. Sources vraies :
-- silver.opensanctions, silver.cnil_sanctions, silver.dgccrf_sanctions
CREATE TABLE gold.compliance_red_flags AS
SELECT
    em.siren,
    em.denomination,
    em.code_ape,
    em.adresse_dept,
    em.insee_etat_administratif,
    em.has_late_filing,
    -- Flags
    (em.insee_etat_administratif = $$F$$) AS is_radiation,
    em.has_late_filing AS has_late_filing_flag,
    EXISTS(
        SELECT 1 FROM silver.opensanctions os
        WHERE os.sirens_fr @> ARRAY[em.siren]::text[]
    ) AS has_sanction,
    EXISTS(
        SELECT 1 FROM silver.cnil_sanctions cs
        WHERE cs.payload->>$$siren$$ = em.siren
    ) AS has_cnil_sanction,
    EXISTS(
        SELECT 1 FROM silver.dgccrf_sanctions ds
        WHERE ds.payload->>$$siren$$ = em.siren
    ) AS has_dgccrf_sanction,
    -- Score risque agrégé 0-100
    (
        (CASE WHEN em.insee_etat_administratif = $$F$$ THEN 50 ELSE 0 END)
        + (CASE WHEN em.has_late_filing THEN 20 ELSE 0 END)
        + (CASE WHEN em.resultat_net_latest IS NOT NULL AND em.resultat_net_latest < 0 THEN 10 ELSE 0 END)
        + (CASE WHEN em.capitaux_propres_latest IS NOT NULL AND em.capitaux_propres_latest < 0 THEN 20 ELSE 0 END)
    )::int AS risk_score,
    NOW() AS materialized_at
FROM gold.entreprises_master em;

CREATE INDEX ON gold.compliance_red_flags (siren);
CREATE INDEX ON gold.compliance_red_flags (risk_score DESC);
CREATE INDEX ON gold.compliance_red_flags (is_radiation) WHERE is_radiation = true;
CREATE INDEX ON gold.compliance_red_flags (has_sanction) WHERE has_sanction = true;

