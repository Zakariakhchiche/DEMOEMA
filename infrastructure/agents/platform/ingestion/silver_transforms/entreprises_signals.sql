-- silver.entreprises_signals — SQL ÉCRIT À LA MAIN (déterministe, sans LLM).
-- Marqué `hand_authored: true` dans le spec → le moteur applique ce fichier tel
-- quel ; le maintainer ne le régénère via LLM que si l'apply/refresh échoue.
--
-- Feature store du scoring M&A (1 row par cible : SAS/SA/SCA, capital >= 100k€,
-- non radiée). Basé sur la définition matérialisée existante (411k lignes), À
-- LAQUELLE on AJOUTE le bloc ratios financiers (grille "Financial ratio
-- assessment") + financial_health_tier + drapeaux de détresse. Toutes les
-- colonnes existantes sont conservées à l'identique (y compris les stubs NULL
-- des features Phase 2 non encore peuplées).

CREATE MATERIALIZED VIEW silver.entreprises_signals AS
WITH cibles AS (
    SELECT
        bie.siren,
        bie.denomination,
        bie.forme_juridique,
        bie.code_ape,
        bie.sigle,
        bie.nom_commercial,
        bie.adresse_code_postal,
        bie.adresse_commune,
        "left"(bie.adresse_code_postal::text, 2) AS adresse_dept,
        bie.adresse_voie,
        bie.adresse_pays,
        bie.date_immatriculation,
        bie.date_debut_activite,
        EXTRACT(year FROM age(now(), bie.date_immatriculation::timestamp without time zone::timestamp with time zone))::integer AS age_entreprise,
        bie.effectif_salarie,
        bie.montant_capital
    FROM (
        SELECT DISTINCT ON (e.siren)
            e.siren, e.denomination, e.forme_juridique, e.code_ape, e.sigle,
            e.nom_commercial, e.adresse_code_postal, e.adresse_commune,
            e.adresse_voie, e.adresse_pays, e.date_immatriculation,
            e.date_debut_activite, e.effectif_salarie, e.montant_capital,
            e.date_radiation
        FROM bronze.inpi_formalites_entreprises e
        ORDER BY e.siren, e.date_immatriculation DESC NULLS LAST
    ) bie
    WHERE bie.forme_juridique = ANY (ARRAY['5710','5720','5730','5485','5499','5505','5510','5515','5520','5530','5540','5599','5385','5308','5306','5202','5203']::text[])
      AND bie.montant_capital >= 100000::numeric
      AND bie.date_radiation IS NULL
),
-- Dernier bilan déposé par SIREN — ÉTENDU avec les postes nécessaires aux ratios.
dernier_bilan AS (
    SELECT DISTINCT ON (c.siren)
        c.siren,
        c.ca_net                AS ca_latest,
        c.capitaux_propres      AS capitaux_propres_latest,
        c.resultat_net          AS resultat_net_latest,
        c.date_cloture          AS bilan_date_cloture,
        c.date_depot            AS bilan_date_depot,
        c.effectif_moyen        AS effectif_moyen_latest,
        c.ca_net,
        c.immo_corporelles,
        c.total_actif,
        c.total_passif,
        c.resultat_exploitation AS resultat_exploitation_latest,   -- EBIT (réel)
        c.dotations_exploitation AS dotations_exploitation_latest, -- amort.+prov. (réel)
        c.emprunts_dettes       AS emprunts_dettes_latest,
        c.creances_clients      AS creances_clients_latest,
        c.stocks                AS stocks_latest,
        c.ca_export             AS ca_export_latest
    FROM silver.inpi_comptes c
    ORDER BY c.siren, c.date_cloture DESC NULLS LAST
),
-- Stats pluriannuelles : volatilité du CA + avant-dernier exercice (croissance).
bilan_stats AS (
    SELECT
        siren,
        stddev_samp(ca_net) AS ca_stddev,
        avg(ca_net)         AS ca_avg,
        (array_agg(ca_net      ORDER BY date_cloture DESC))[2] AS ca_avant_dernier,
        (array_agg(total_actif ORDER BY date_cloture DESC))[2] AS total_actif_avant_dernier
    FROM silver.inpi_comptes
    GROUP BY siren
),
dirigeants_par_siren AS (
    SELECT su.siren, d.nom, d.prenom, d.age_2026, d.n_mandats_actifs, d.n_sci, d.total_capital_sci
    FROM silver.inpi_dirigeants d
    CROSS JOIN LATERAL unnest(d.sirens_mandats) su(siren)
),
agg_dirigeants AS (
    SELECT
        dps.siren,
        max(dps.age_2026)         AS age_dirigeant_max,
        sum(dps.n_sci)            AS n_sci_dirigeants,
        sum(dps.total_capital_sci) AS total_capital_sci,
        max(dps.n_mandats_actifs) AS n_mandats_dirigeant_max,
        count(*)                  AS n_dirigeants
    FROM dirigeants_par_siren dps
    WHERE dps.siren IN (SELECT cibles.siren FROM cibles)
    GROUP BY dps.siren
),
n_exercices AS (
    SELECT siren, count(DISTINCT date_cloture) AS n_exercices_deposes
    FROM silver.inpi_comptes
    GROUP BY siren
),
base AS (
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
        a.age_dirigeant_max,
        a.age_dirigeant_max IS NOT NULL AND a.age_dirigeant_max >= 60 AS has_dirigeant_senior,
        a.n_sci_dirigeants,
        a.total_capital_sci,
        COALESCE(a.n_sci_dirigeants, 0::numeric) >= 2::numeric AS has_holding_patrimoniale,
        a.n_mandats_dirigeant_max,
        COALESCE(a.n_mandats_dirigeant_max, 0::bigint) >= 5 AS has_pro_ma,
        a.n_dirigeants,
        b.ca_latest,
        b.capitaux_propres_latest,
        b.resultat_net_latest,
        ne.n_exercices_deposes,
        b.bilan_date_cloture IS NOT NULL AND b.bilan_date_cloture > (now()::date - '2 years'::interval) AS has_bilan_recent,
        b.effectif_moyen_latest,
        b.immo_corporelles,
        b.total_actif > 0::numeric AND (b.immo_corporelles / NULLIF(b.total_actif, 0::numeric)) > 0.3 AS immo_corporelles_high,
        b.bilan_date_depot IS NOT NULL AND b.bilan_date_cloture IS NOT NULL AND b.bilan_date_depot > (b.bilan_date_cloture + '7 mons'::interval) AS has_late_filing,
        -- ─── features Phase 2 conservées en stub (inchangées) ───
        NULL::integer AS n_contentieux,
        NULL::boolean AS has_contentieux_recent,
        NULL::boolean AS has_sanction,
        NULL::boolean AS has_sanction_dirigeant,
        NULL::integer AS n_press_mentions_90d,
        NULL::boolean AS has_cession_detected,
        NULL::integer AS digital_presence_score,
        NULL::boolean AS has_website,
        NULL::boolean AS has_brevets,
        NULL::boolean AS has_marques,
        NULL::boolean AS has_published_ges_recent,
        NULL::numeric AS emissions_total_tco2e,
        NULL::numeric AS ca_export_ratio,
        NULL::boolean AS has_filiale_etranger,
        NULL::boolean AS has_lei_code,
        NULL::integer AS n_marches_publics,
        NULL::numeric AS total_montant_marches,
        NULL::boolean AS is_dependant_commande_publique,
        NULL::boolean AS has_offshore_link,
        NULL::boolean AS is_lobbying_registered,
        NULL::numeric AS chiffre_affaires_lobbying,
        NULL::boolean AS has_kol_pharma,
        NULL::boolean AS has_treasury_excess,
        NULL::boolean AS has_successeur_probable,
        -- ─── NOUVEAU : colonnes financières latest (pour les ratios) ───
        b.resultat_exploitation_latest,
        b.total_actif        AS total_actif_latest,
        b.total_passif       AS total_passif_latest,
        b.emprunts_dettes_latest,
        b.creances_clients_latest,
        b.stocks_latest,
        b.ca_export_latest,
        bs.ca_avant_dernier,
        bs.total_actif_avant_dernier,
        -- ─── Ratios financiers. NULLIF anti-DIV/0 ───
        -- EBITDA RÉEL = résultat d'exploitation (EBIT) + dotations amort./prov.
        -- (au lieu du proxy = EBIT seul). Données 100% issues de la liasse INPI.
        (b.resultat_exploitation_latest + COALESCE(b.dotations_exploitation_latest, 0)) AS proxy_ebitda,
        (b.resultat_exploitation_latest + COALESCE(b.dotations_exploitation_latest, 0)) / NULLIF(b.ca_latest, 0) AS ebitda_margin,
        b.resultat_exploitation_latest / NULLIF(b.ca_latest, 0)            AS ebit_margin,
        b.resultat_net_latest          / NULLIF(b.ca_latest, 0)           AS net_margin,
        (b.resultat_exploitation_latest + COALESCE(b.dotations_exploitation_latest, 0)) / NULLIF((COALESCE(b.total_actif,0) + COALESCE(bs.total_actif_avant_dernier, b.total_actif)) / 2.0, 0) AS ebitda_on_assets,
        b.emprunts_dettes_latest       / NULLIF((b.resultat_exploitation_latest + COALESCE(b.dotations_exploitation_latest, 0)), 0) AS debt_to_ebitda,
        b.emprunts_dettes_latest       / NULLIF(b.capitaux_propres_latest, 0) AS debt_to_equity,
        (COALESCE(b.total_actif, 0) - COALESCE(b.capitaux_propres_latest, 0)) / NULLIF(b.total_actif, 0) AS debt_ratio,
        b.capitaux_propres_latest      / NULLIF(b.total_passif, 0)        AS equity_ratio,
        b.creances_clients_latest      / NULLIF(b.ca_latest, 0) * 365.0   AS dso_days,
        b.ca_export_latest             / NULLIF(b.ca_latest, 0)           AS ca_export_ratio_calc,
        bs.ca_stddev                   / NULLIF(bs.ca_avg, 0)             AS revenue_volatility,
        (b.ca_latest - bs.ca_avant_dernier) / NULLIF(bs.ca_avant_dernier, 0) AS revenue_growth_yoy,
        -- ─── NOUVEAU : drapeaux de détresse (alimentent compliance + Dim 3) ───
        b.capitaux_propres_latest < 0      AS has_negative_equity,
        -- Détresse calculée sur l'EBITDA RÉEL (EBIT + dotations), pas sur l'EBIT seul.
        (b.resultat_exploitation_latest + COALESCE(b.dotations_exploitation_latest, 0)) < 0 AS has_negative_ebitda,
        (b.emprunts_dettes_latest / NULLIF((b.resultat_exploitation_latest + COALESCE(b.dotations_exploitation_latest, 0)), 0) > 4
            OR b.emprunts_dettes_latest / NULLIF(b.capitaux_propres_latest, 0) > 2) AS has_high_leverage,
        ((b.ca_latest - bs.ca_avant_dernier) / NULLIF(bs.ca_avant_dernier, 0)) < -0.15 AS has_revenue_decline
    FROM cibles c
    LEFT JOIN agg_dirigeants a  ON a.siren = c.siren
    LEFT JOIN dernier_bilan b   ON b.siren = c.siren
    LEFT JOIN n_exercices ne    ON ne.siren = c.siren
    LEFT JOIN bilan_stats bs    ON bs.siren = c.siren
)
SELECT
    base.*,
    -- ─── NOUVEAU : tier global (grille above/average/below) ───
    CASE
        WHEN base.ebitda_margin IS NULL AND base.debt_to_equity IS NULL THEN 'unknown'
        WHEN base.has_negative_equity OR base.has_negative_ebitda
             OR base.debt_to_ebitda > 4 THEN 'below_average'
        WHEN base.ebitda_margin >= 0.15 AND COALESCE(base.debt_to_equity, 0) < 0.6 THEN 'above_average'
        ELSE 'average'
    END AS financial_health_tier,
    now() AS materialized_at
FROM base;

-- Index existants conservés
CREATE INDEX entreprises_signals_siren_idx                    ON silver.entreprises_signals USING btree (siren);
CREATE INDEX entreprises_signals_ca_latest_idx                ON silver.entreprises_signals USING btree (ca_latest DESC NULLS LAST);
CREATE INDEX entreprises_signals_age_dirigeant_max_idx        ON silver.entreprises_signals USING btree (age_dirigeant_max DESC NULLS LAST);
CREATE INDEX entreprises_signals_code_ape_idx                 ON silver.entreprises_signals USING btree (code_ape);
CREATE INDEX entreprises_signals_adresse_dept_idx             ON silver.entreprises_signals USING btree (adresse_dept);
CREATE INDEX entreprises_signals_has_pro_ma_idx               ON silver.entreprises_signals USING btree (has_pro_ma) WHERE (has_pro_ma = true);
CREATE INDEX entreprises_signals_has_holding_patrimoniale_idx ON silver.entreprises_signals USING btree (has_holding_patrimoniale) WHERE (has_holding_patrimoniale = true);
-- Index nouveaux (ratios / détresse)
CREATE INDEX entreprises_signals_ebitda_margin_idx            ON silver.entreprises_signals USING btree (ebitda_margin DESC NULLS LAST);
CREATE INDEX entreprises_signals_debt_to_ebitda_idx           ON silver.entreprises_signals USING btree (debt_to_ebitda DESC NULLS LAST);
CREATE INDEX entreprises_signals_financial_health_tier_idx    ON silver.entreprises_signals USING btree (financial_health_tier);
CREATE INDEX entreprises_signals_has_negative_equity_idx      ON silver.entreprises_signals USING btree (has_negative_equity) WHERE (has_negative_equity = true);
CREATE INDEX entreprises_signals_has_high_leverage_idx        ON silver.entreprises_signals USING btree (has_high_leverage) WHERE (has_high_leverage = true);
