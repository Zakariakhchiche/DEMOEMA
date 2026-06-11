-- silver.sci_master — SQL ÉCRIT À LA MAIN (déterministe, sans LLM).
-- Marqué `hand_authored: true` dans le spec → appliqué tel quel ; le maintainer
-- ne régénère via LLM que si l'apply/refresh échoue.
--
-- Capturé depuis la définition MATÉRIALISÉE EN PRODUCTION (pg_get_viewdef) le
-- 2026-06-11. La vue live est plus simple que l'ancien brouillon hand-écrit du
-- 2026-05-03 (qui ajoutait dirigeants top-5 / zone DVF mais n'a jamais été
-- déployé et embarquait un join lent) — on fige donc l'EXACT comportement prod
-- pour ne rien casser chez les consommateurs (gold.sci_master).
-- patrimoine_net_estime / estimation_value_* utilisent capitaux_propres et
-- emprunts_dettes de silver.inpi_comptes → bénéficient du fix passif (m1 vs m3).

CREATE MATERIALIZED VIEW silver.sci_master AS
WITH sci_base AS (
    SELECT DISTINCT ON (e.siren) e.siren,
        e.denomination, e.forme_juridique, e.code_ape, e.sigle, e.nom_commercial,
        e.adresse_voie, e.adresse_code_postal,
        "left"(e.adresse_code_postal::text, 2) AS adresse_dept,
        e.adresse_pays, e.date_immatriculation,
        e.montant_capital AS capital_social,
        EXTRACT(year FROM age(now(), e.date_immatriculation::timestamp with time zone))::integer AS age_entreprise,
        e.forme_juridique ~~ '65%'::text AS is_sci,
        (e.forme_juridique = ANY (ARRAY['5499'::text, '5710'::text])) AND (e.denomination ~~* '%PATRIMOINE%'::text OR e.denomination ~~* '%HOLDING%'::text OR e.denomination ~~* '%FAMIL%'::text OR e.denomination ~~* '%MAISON %'::text) AS is_holding_patrimoniale
    FROM bronze.inpi_formalites_entreprises e
    WHERE e.siren IS NOT NULL AND (e.forme_juridique ~~ '65%'::text OR (e.forme_juridique = ANY (ARRAY['5499'::text, '5710'::text])) AND (e.denomination ~~* '%PATRIMOINE%'::text OR e.denomination ~~* '%HOLDING%'::text OR e.denomination ~~* '%FAMIL%'::text OR e.denomination ~~* '%MAISON %'::text))
    ORDER BY e.siren, e.updated_at_src DESC NULLS LAST
), last_bilan AS (
    SELECT DISTINCT ON (c.siren) c.siren,
        c.ca_net, c.resultat_net, c.total_actif, c.immo_corporelles,
        c.capitaux_propres, c.emprunts_dettes, c.effectif_moyen, c.date_cloture
    FROM silver.inpi_comptes c
    WHERE (c.siren IN (SELECT sci_base.siren FROM sci_base))
    ORDER BY c.siren, c.date_cloture DESC NULLS LAST
), ownership AS (
    SELECT p.siren,
        count(*) FILTER (WHERE p.type_de_personne = 'INDIVIDU'::text AND p.actif = true) AS n_dirigeants_individu,
        count(*) FILTER (WHERE p.type_de_personne = 'PERSONNE_MORALE'::text AND p.actif = true) AS n_dirigeants_morale,
        array_agg(DISTINCT p.entreprise_siren) FILTER (WHERE p.type_de_personne = 'PERSONNE_MORALE'::text AND p.actif = true AND p.entreprise_siren IS NOT NULL) AS parent_sirens_raw,
        array_agg(DISTINCT p.entreprise_denomination) FILTER (WHERE p.type_de_personne = 'PERSONNE_MORALE'::text AND p.actif = true AND p.entreprise_denomination IS NOT NULL) AS parent_denominations
    FROM bronze.inpi_formalites_personnes p
    JOIN sci_base sb ON sb.siren = p.siren
    GROUP BY p.siren
)
SELECT s.siren,
    s.denomination, s.forme_juridique, s.code_ape, s.sigle, s.nom_commercial,
    s.is_sci, s.is_holding_patrimoniale,
    s.adresse_voie, s.adresse_code_postal, s.adresse_dept, s.adresse_pays,
    s.date_immatriculation, s.age_entreprise, s.capital_social,
    lb.total_actif, lb.immo_corporelles,
    GREATEST(COALESCE(lb.total_actif, 0::numeric) - COALESCE(lb.immo_corporelles, 0::numeric), 0::numeric) AS immo_financieres,
    COALESCE(lb.immo_corporelles, 0::numeric) AS immo_total,
    lb.capitaux_propres, lb.emprunts_dettes,
    CASE
        WHEN lb.total_actif IS NOT NULL THEN COALESCE(lb.total_actif, 0::numeric) - COALESCE(lb.emprunts_dettes, 0::numeric)
        WHEN lb.immo_corporelles IS NOT NULL THEN lb.immo_corporelles
        ELSE NULL::numeric
    END AS patrimoine_net_estime,
    lb.ca_net, lb.resultat_net, lb.effectif_moyen,
    lb.date_cloture AS date_cloture_dernier_bilan,
    lb.date_cloture >= (now() - '2 years'::interval)::date AS has_bilan_recent,
    COALESCE(o.n_dirigeants_individu, 0::bigint) AS n_dirigeants_individu,
    COALESCE(o.n_dirigeants_morale, 0::bigint) AS n_dirigeants_morale,
    CASE
        WHEN COALESCE(o.n_dirigeants_morale, 0::bigint) = 0 AND COALESCE(o.n_dirigeants_individu, 0::bigint) > 0 THEN 'individual'::text
        WHEN COALESCE(o.n_dirigeants_individu, 0::bigint) = 0 AND COALESCE(o.n_dirigeants_morale, 0::bigint) > 0 THEN 'corporate'::text
        WHEN COALESCE(o.n_dirigeants_individu, 0::bigint) > 0 AND COALESCE(o.n_dirigeants_morale, 0::bigint) > 0 THEN 'mixed'::text
        ELSE 'unknown'::text
    END AS ownership_type,
    o.parent_sirens_raw AS parent_sirens,
    o.parent_denominations,
    lb.immo_corporelles AS estimation_value_min_eur,
    (COALESCE(lb.immo_corporelles, 0::numeric) + COALESCE(lb.total_actif, 0::numeric) - COALESCE(lb.emprunts_dettes, 0::numeric)) / 2.0 AS estimation_value_avg_eur,
    lb.total_actif AS estimation_value_max_eur,
    now() AS materialized_at
FROM sci_base s
LEFT JOIN last_bilan lb ON lb.siren = s.siren
LEFT JOIN ownership o ON o.siren = s.siren;

CREATE UNIQUE INDEX sci_master_siren_idx          ON silver.sci_master USING btree (siren);
CREATE INDEX sci_master_patrimoine_net_idx        ON silver.sci_master USING btree (patrimoine_net_estime DESC NULLS LAST);
CREATE INDEX sci_master_ownership_type_idx        ON silver.sci_master USING btree (ownership_type);
CREATE INDEX sci_master_adresse_dept_idx          ON silver.sci_master USING btree (adresse_dept);
CREATE INDEX sci_master_is_sci_idx                ON silver.sci_master USING btree (is_sci) WHERE (is_sci = true);
CREATE INDEX sci_master_has_bilan_recent_idx      ON silver.sci_master USING btree (has_bilan_recent) WHERE (has_bilan_recent = true);
