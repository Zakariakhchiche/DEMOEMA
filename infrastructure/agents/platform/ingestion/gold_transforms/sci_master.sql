-- gold.sci_master — feature store M&A SCI consommable produit
-- Hand-written 2026-05-03 (cache pour éviter re-génération LLM Ollama).
-- Spec : gold_specs/sci_master.yaml
--
-- 1 row par siren SCI/holding patrimoniale avec scoring M&A composite,
-- tier (A_HOT/B_WARM/C_PIPELINE/D_WATCH/E_REJECT) et valuation estimée.
--
-- Sources :
--   silver.sci_master              -- base (Phase 1, doit exister d'abord)
--   silver.bodacc_annonces         -- events 24m
--   silver.opensanctions           -- compliance
--   silver.icij_offshore_match    -- offshore
--   silver.judilibre_decisions    -- litigation
--   silver.gleif_lei              -- parent LEI

CREATE MATERIALIZED VIEW gold.sci_master AS
WITH

-- ───────── BODACC events 24 derniers mois ─────────
bodacc_agg AS (
    SELECT
        b.siren,
        count(*) AS bodacc_n_events_24m,
        bool_or(b.type_avis ILIKE '%cession%' OR b.type_avis ILIKE '%vente%') AS bodacc_has_cession_event,
        bool_or(b.type_avis ILIKE '%capital%') AS bodacc_has_modif_capital_event,
        bool_or(b.type_avis ILIKE '%dirigeant%' OR b.type_avis ILIKE '%représentant%') AS bodacc_has_modif_dirigeant_event,
        bool_or(b.type_avis ILIKE '%dissolution%' OR b.type_avis ILIKE '%radiation%') AS bodacc_has_dissolution_event,
        max(b.date_parution) AS bodacc_last_event_date
    FROM silver.bodacc_annonces b
    WHERE b.date_parution >= now() - interval '24 months'
      AND b.siren IN (SELECT siren FROM silver.sci_master)
    GROUP BY b.siren
),

-- ───────── Compliance signaux ─────────
sanctions_match AS (
    SELECT DISTINCT siren
    FROM silver.opensanctions
    WHERE siren IS NOT NULL
      AND siren IN (SELECT siren FROM silver.sci_master)
),

offshore_match AS (
    SELECT DISTINCT siren_fr AS siren
    FROM silver.icij_offshore_match
    WHERE siren_fr IS NOT NULL
      AND siren_fr IN (SELECT siren FROM silver.sci_master)
),

judilibre_match AS (
    SELECT DISTINCT siren
    FROM silver.judilibre_decisions
    WHERE siren IS NOT NULL
      AND siren IN (SELECT siren FROM silver.sci_master)
),

-- ───────── LEI parents (chaîne corporate) ─────────
lei_parent AS (
    SELECT
        l.siren_fr AS siren,
        l.lei,
        l.parent_lei,
        l.ultimate_parent_lei,
        l.country_code AS ultimate_parent_country
    FROM silver.gleif_lei l
    WHERE l.siren_fr IS NOT NULL
      AND l.siren_fr IN (SELECT siren FROM silver.sci_master)
),

-- ───────── Scoring 6 axes ─────────
scored AS (
    SELECT
        s.*,

        -- 1) Patrimoine net score (log normalisé 100k€ → 0 / 50M€ → 100)
        ROUND(
            LEAST(100.0, GREATEST(0.0,
                100.0 * (LN(GREATEST(s.patrimoine_net_estime, 1) + 1) - LN(100000))
                / NULLIF(LN(50000000) - LN(100000), 0)
            ))
        )::int AS patrimoine_net_score,

        -- 2) Transmission score (basé age + has_successeur)
        CASE
            WHEN s.age_dirigeant_max >= 70 THEN 90
            WHEN s.age_dirigeant_max >= 60 AND s.has_successeur THEN 80
            WHEN s.age_dirigeant_max >= 60 THEN 70
            WHEN s.age_dirigeant_max >= 50 THEN 50
            ELSE 30
        END AS transmission_score,

        -- 3) Compliance score (inverse signaux)
        CASE
            WHEN sa.siren IS NOT NULL OR ofs.siren IS NOT NULL OR jd.siren IS NOT NULL THEN 0
            WHEN s.has_bilan_recent = false THEN 50  -- retard dépôt = stress
            ELSE 100
        END AS compliance_score,

        -- 4) Structure score (simplicité ownership)
        CASE
            WHEN s.ownership_type = 'individual' THEN 95
            WHEN s.ownership_type = 'mixed' THEN 70
            WHEN s.ownership_type = 'corporate' AND lp.ultimate_parent_lei IS NULL THEN 60
            WHEN s.ownership_type = 'corporate' AND lp.ultimate_parent_lei IS NOT NULL THEN 40  -- groupe complexe
            ELSE 50
        END AS structure_score,

        -- 5) Liquidité score (loyers vs patrimoine)
        ROUND(
            LEAST(100.0, GREATEST(0.0,
                100.0 * COALESCE(s.ca_net::numeric / NULLIF(s.total_actif, 0), 0)
            ))
        )::int AS liquidite_score,

        -- 6) Diversification géo score (1 CP = 25, 2 CP = 50, 3 = 75, 4+ = 100)
        -- Pour 1 SCI single, on a 1 seul CP → 25.
        25 AS diversification_geo_score,

        -- Compliance flags individuels
        (sa.siren IS NOT NULL) AS has_sanction,
        (ofs.siren IS NOT NULL) AS has_offshore_match,
        (jd.siren IS NOT NULL) AS has_judilibre_decision,

        -- LEI parent
        lp.lei,
        lp.ultimate_parent_lei,
        lp.ultimate_parent_country,
        (lp.lei IS NOT NULL) AS has_lei_parent,

        -- BODACC
        COALESCE(bo.bodacc_n_events_24m, 0) AS bodacc_n_events_24m,
        COALESCE(bo.bodacc_has_cession_event, false) AS bodacc_has_cession_event,
        COALESCE(bo.bodacc_has_modif_capital_event, false) AS bodacc_has_modif_capital_event,
        COALESCE(bo.bodacc_has_modif_dirigeant_event, false) AS bodacc_has_modif_dirigeant_event,
        COALESCE(bo.bodacc_has_dissolution_event, false) AS bodacc_has_dissolution_event,
        bo.bodacc_last_event_date
    FROM silver.sci_master s
    LEFT JOIN bodacc_agg bo ON bo.siren = s.siren
    LEFT JOIN sanctions_match sa ON sa.siren = s.siren
    LEFT JOIN offshore_match ofs ON ofs.siren = s.siren
    LEFT JOIN judilibre_match jd ON jd.siren = s.siren
    LEFT JOIN lei_parent lp ON lp.siren = s.siren
)

-- ───────── ASSEMBLY FINAL avec deal_score + tier + valuation ─────────
SELECT
    sc.*,

    -- ⭐ Deal score composite pondéré
    ROUND(
        0.30 * sc.patrimoine_net_score
      + 0.20 * sc.transmission_score
      + 0.15 * sc.compliance_score
      + 0.15 * sc.structure_score
      + 0.10 * sc.liquidite_score
      + 0.10 * sc.diversification_geo_score
    )::int AS deal_score,

    -- ⭐ Tier
    CASE
        WHEN ROUND(
            0.30 * sc.patrimoine_net_score + 0.20 * sc.transmission_score
          + 0.15 * sc.compliance_score + 0.15 * sc.structure_score
          + 0.10 * sc.liquidite_score + 0.10 * sc.diversification_geo_score
        )::int >= 80 THEN 'A_HOT'
        WHEN ROUND(
            0.30 * sc.patrimoine_net_score + 0.20 * sc.transmission_score
          + 0.15 * sc.compliance_score + 0.15 * sc.structure_score
          + 0.10 * sc.liquidite_score + 0.10 * sc.diversification_geo_score
        )::int >= 60 THEN 'B_WARM'
        WHEN ROUND(
            0.30 * sc.patrimoine_net_score + 0.20 * sc.transmission_score
          + 0.15 * sc.compliance_score + 0.15 * sc.structure_score
          + 0.10 * sc.liquidite_score + 0.10 * sc.diversification_geo_score
        )::int >= 40 THEN 'C_PIPELINE'
        WHEN ROUND(
            0.30 * sc.patrimoine_net_score + 0.20 * sc.transmission_score
          + 0.15 * sc.compliance_score + 0.15 * sc.structure_score
          + 0.10 * sc.liquidite_score + 0.10 * sc.diversification_geo_score
        )::int >= 20 THEN 'D_WATCH'
        ELSE 'E_REJECT'
    END AS tier,

    -- ⭐ Valuation estimée — multiple sectoriel SCI
    CASE
        WHEN sc.ownership_type = 'individual' THEN COALESCE(sc.patrimoine_net_estime, 0) * 1.0
        WHEN sc.ownership_type = 'corporate' THEN COALESCE(sc.patrimoine_net_estime, 0) * 1.2
        WHEN sc.ownership_type = 'mixed' THEN COALESCE(sc.patrimoine_net_estime, 0) * 1.1
        ELSE COALESCE(sc.patrimoine_net_estime, 0)
    END AS valuation_estimee_eur,

    -- Data quality score (% colonnes non-NULL clés)
    ROUND(100.0 * (
        (CASE WHEN sc.code_ape IS NOT NULL THEN 1 ELSE 0 END)
      + (CASE WHEN sc.adresse_code_postal IS NOT NULL THEN 1 ELSE 0 END)
      + (CASE WHEN sc.total_actif IS NOT NULL THEN 1 ELSE 0 END)
      + (CASE WHEN sc.ownership_type != 'unknown' THEN 1 ELSE 0 END)
      + (CASE WHEN sc.age_dirigeant_max IS NOT NULL THEN 1 ELSE 0 END)
    ) / 5.0)::int AS data_quality_score,

    now() AS gold_materialized_at
FROM scored sc
;

-- Indexes principaux
CREATE UNIQUE INDEX gold_sci_master_siren_idx ON gold.sci_master (siren);
CREATE INDEX gold_sci_master_deal_score_idx ON gold.sci_master (deal_score DESC);
CREATE INDEX gold_sci_master_tier_idx ON gold.sci_master (tier);
CREATE INDEX gold_sci_master_patrimoine_net_idx ON gold.sci_master (patrimoine_net_estime DESC NULLS LAST);
CREATE INDEX gold_sci_master_valuation_idx ON gold.sci_master (valuation_estimee_eur DESC NULLS LAST);
CREATE INDEX gold_sci_master_ownership_type_idx ON gold.sci_master (ownership_type);
CREATE INDEX gold_sci_master_adresse_dept_idx ON gold.sci_master (adresse_dept);
CREATE INDEX gold_sci_master_has_cession_idx ON gold.sci_master (bodacc_has_cession_event) WHERE bodacc_has_cession_event = true;
