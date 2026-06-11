-- silver.inpi_comptes — SQL ÉCRIT À LA MAIN (déterministe, sans LLM).
-- Marqué `hand_authored: true` dans le spec → appliqué tel quel ; le maintainer
-- ne régénère via LLM que si l'apply/refresh échoue.
--
-- Vue flat des bilans INPI : 1 row par dépôt, postes financiers extraits des
-- liasses (bronze.inpi_comptes_liasses) par code XBRL.
--
-- 🔧 CORRECTION 2026-06-11 (bug d'extraction du PASSIF) :
--   Les codes du PASSIF (DL capitaux_propres, DR/EE total_passif, DU
--   emprunts_dettes) stockent leur valeur dans la colonne m1 (page passif CERFA
--   2051 = 2 colonnes N/N-1), PAS dans m3. L'ancienne version lisait `l.m3`
--   pour ces codes → 100% NULL sur 6,27M dépôts (capitaux_propres, total_passif,
--   emprunts_dettes vides), ce qui cassait tous les ratios dette/solvabilité.
--   Fix : COALESCE(l.m1, l.m3) pour les postes passif (m1 prioritaire).
--   L'ACTIF (CO, BX, BZ, CJ, CF, BJ) reste en m3 (page actif = 4 colonnes,
--   net N en m3) — inchangé.

CREATE MATERIALIZED VIEW silver.inpi_comptes AS
SELECT
    d.depot_id,
    d.siren,
    d.denomination,
    d.date_cloture,
    d.date_depot,
    d.type_bilan,
    d.confidentiality,
    -- ─── Compte de résultat (page 3, total N en m3, France en m1) ───
    max(CASE WHEN l.code::text = 'FL' THEN COALESCE(l.m3, l.m1) END) AS ventes_marchandises,
    max(CASE WHEN l.code::text = 'FJ' THEN l.m1 END)                 AS ca_france,
    max(CASE WHEN l.code::text = 'FK' THEN l.m1 END)                 AS ca_export,
    max(CASE WHEN l.code::text = 'FR' THEN COALESCE(l.m3, l.m1) END) AS ca_net,
    max(CASE WHEN l.code::text = 'HN' THEN COALESCE(l.m1, l.m3) END) AS resultat_net,
    max(CASE WHEN l.code::text = 'HH' THEN COALESCE(l.m1, l.m3) END) AS resultat_avant_impot,
    max(CASE WHEN l.code::text = 'GG' THEN COALESCE(l.m1, l.m3) END) AS resultat_exploitation,
    -- ─── ACTIF (page 1, net N en m3) — inchangé ───
    max(CASE WHEN l.code::text = 'CO' THEN l.m3 END) AS total_actif,
    max(CASE WHEN l.code::text = 'BJ' THEN l.m3 END) AS immo_incorporelles,
    max(CASE WHEN l.code::text = 'BX' THEN l.m3 END) AS immo_corporelles,
    max(CASE WHEN l.code::text = 'BZ' THEN l.m3 END) AS immo_financieres,
    max(CASE WHEN l.code::text = 'CJ' THEN l.m3 END) AS stocks,
    max(CASE WHEN l.code::text = 'CF' THEN l.m3 END) AS creances_clients,
    -- ─── PASSIF (page 2, valeur N en m1) — CORRIGÉ : COALESCE(m1, m3) ───
    max(CASE WHEN l.code::text = 'DA' THEN COALESCE(l.m1, l.m3) END) AS capital_social,
    max(CASE WHEN l.code::text = 'DL' THEN COALESCE(l.m1, l.m3) END) AS capitaux_propres,
    COALESCE(
        max(CASE WHEN l.code::text = 'EE' THEN COALESCE(l.m1, l.m3) END),   -- TOTAL GÉNÉRAL passif (bien peuplé)
        max(CASE WHEN l.code::text = 'DR' THEN COALESCE(l.m1, l.m3) END)    -- fallback sous-total
    ) AS total_passif,
    max(CASE WHEN l.code::text = 'DU' THEN COALESCE(l.m1, l.m3) END) AS emprunts_dettes,
    max(CASE WHEN l.code::text = 'YP' THEN l.m1 END) AS effectif_moyen,
    d.updated_at_src,
    count(l.code) AS n_liasses_lignes,
    now() AS materialized_at
FROM bronze.inpi_comptes_depots d
LEFT JOIN bronze.inpi_comptes_liasses l USING (depot_id)
GROUP BY d.depot_id, d.siren, d.denomination, d.date_cloture, d.date_depot,
         d.type_bilan, d.confidentiality, d.updated_at_src;

CREATE INDEX inpi_comptes_siren_idx              ON silver.inpi_comptes USING btree (siren);
CREATE INDEX inpi_comptes_date_cloture_idx       ON silver.inpi_comptes USING btree (date_cloture DESC NULLS LAST);
CREATE INDEX inpi_comptes_siren_date_cloture_idx ON silver.inpi_comptes USING btree (siren, date_cloture DESC NULLS LAST);
CREATE INDEX inpi_comptes_type_bilan_idx         ON silver.inpi_comptes USING btree (type_bilan);
