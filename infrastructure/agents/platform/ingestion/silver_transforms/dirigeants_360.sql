-- silver.dirigeants_360 — SQL ÉCRIT À LA MAIN (déterministe, sans LLM).
-- Marqué `hand_authored: true` dans le spec → appliqué tel quel ; le maintainer
-- ne régénère via LLM que si l'apply/refresh échoue.
--
-- Vue 360° du dirigeant : identité INPI + patrimoine SCI + finances agrégées +
-- sanctions + OSINT + pro_ma_score. 1 row par person_uid.
--
-- 🔧 RÉÉCRITURE 2026-06-11 : la version générée par le LLM ne finissait jamais
--    (build bloqué > 1h). Elle cumulait 4 anti-patterns de performance :
--    1. finances = 3 sous-requêtes CORRÉLÉES par dirigeant (24M exécutions
--       contre inpi_comptes 6,3M) → ici : un seul CTE pré-agrégé (unnest +
--       join + GROUP BY).
--    2. sanctions = EXISTS ILIKE '%nom%' wildcard corrélé → ici : semi-join sur
--       clé de nom normalisée contre un set dédupliqué.
--    3. SCI = JOIN sur UPPER(unaccent(...)) des 2 côtés (non indexable, many×many)
--       → ici : clés normalisées pré-calculées + SCI dédupliqué (DISTINCT ON).
--    4. OSINT = même anti-pattern fonction → idem clés normalisées.
--    Sémantique des colonnes préservée à l'identique.

CREATE MATERIALIZED VIEW silver.dirigeants_360 AS
WITH base AS (
    SELECT
        md5(coalesce(nom,'') || '|' || coalesce(prenom,'') || '|' || coalesce(date_naissance,'')) AS person_uid,
        nom, prenom, date_naissance, age_2026,
        sirens_mandats, denominations, formes_juridiques, roles,
        n_mandats_actifs, n_mandats_total, is_multi_mandat,
        first_mandat_date, last_mandat_date,
        array_length(sirens_mandats, 1) AS n_companies,
        -- clés normalisées pré-calculées (une fois par row, équi-jointures ensuite)
        upper(unaccent(coalesce(nom,'')))    AS nom_key,
        upper(unaccent(coalesce(prenom,''))) AS prenom_key,
        coalesce(date_naissance,'')          AS dn_key,
        -- variantes de nom complet normalisé pour le semi-join sanctions
        regexp_replace(lower(unaccent(coalesce(prenom,'') || ' ' || coalesce(nom,''))), '\s+', ' ', 'g') AS name_key_pn,
        regexp_replace(lower(unaccent(coalesce(nom,'') || ' ' || coalesce(prenom,''))), '\s+', ' ', 'g') AS name_key_np
    FROM silver.inpi_dirigeants
    WHERE nom IS NOT NULL AND prenom IS NOT NULL
),
-- Fix #1 : finances pré-agrégées (remplace 3 sous-requêtes corrélées/dirigeant).
-- On réduit d'abord inpi_comptes au DERNIER exercice par siren (CA courant, pas
-- la somme de tous les exercices comme le faisait l'ancien SQL) — correct ET
-- effondre le volume de jointure (de 1,2 Md à ~81M lignes).
comptes_latest AS (
    SELECT DISTINCT ON (siren)
        siren, ca_net, resultat_net, date_cloture
    FROM silver.inpi_comptes
    ORDER BY siren, date_cloture DESC NULLS LAST
),
finances AS (
    SELECT
        b.person_uid,
        sum(cl.ca_net)        AS ca_total,
        sum(cl.resultat_net)  AS resultat_net_total,
        count(DISTINCT cl.siren) FILTER (WHERE cl.date_cloture > CURRENT_DATE - INTERVAL '24 months') AS n_companies_avec_bilan_recent
    FROM base b
    CROSS JOIN LATERAL unnest(b.sirens_mandats) AS m(siren)
    JOIN comptes_latest cl ON cl.siren = m.siren
    GROUP BY b.person_uid
),
-- Fix #3 : SCI dédupliqué à 1 row par personne, clés normalisées.
sci AS (
    SELECT DISTINCT ON (upper(unaccent(coalesce(nom,''))), upper(unaccent(coalesce(prenom,''))), coalesce(date_naissance,''))
        upper(unaccent(coalesce(nom,'')))    AS nom_key,
        upper(unaccent(coalesce(prenom,''))) AS prenom_key,
        coalesce(date_naissance,'')          AS dn_key,
        n_sci, total_capital_sci, sci_denominations, sci_code_postaux, first_sci_date
    FROM silver.dirigeant_sci_patrimoine
    ORDER BY upper(unaccent(coalesce(nom,''))), upper(unaccent(coalesce(prenom,''))),
             coalesce(date_naissance,''), total_capital_sci DESC NULLS LAST
),
-- Fix #4 : OSINT clés normalisées.
osint AS (
    SELECT
        upper(unaccent(coalesce(nom,''))) AS nom_key,
        coalesce(date_naissance,'')       AS dn_key,
        prenoms,
        has_linkedin, has_github, has_any_social,
        n_linkedin, n_github, n_twitter, n_total_social,
        denomination_main_company, last_scanned_at
    FROM silver.osint_persons_enriched
),
-- Fix #2 : set de noms sanctionnés normalisés (semi-join, plus d'ILIKE wildcard).
sanctions_keys AS (
    SELECT DISTINCT regexp_replace(lower(unaccent(name)), '\s+', ' ', 'g') AS name_key
    FROM silver.opensanctions
    WHERE schema = 'Person' AND name IS NOT NULL AND length(name) >= 6
),
enriched AS (
    SELECT DISTINCT ON (b.person_uid)
        b.person_uid, b.nom, b.prenom, b.date_naissance, b.age_2026,
        b.sirens_mandats, b.denominations, b.formes_juridiques, b.roles,
        b.n_mandats_actifs, b.n_mandats_total, b.is_multi_mandat,
        b.first_mandat_date, b.last_mandat_date, b.n_companies,
        sci.n_sci                     AS n_sci,
        sci.total_capital_sci         AS total_capital_sci,
        sci.sci_denominations,
        sci.sci_code_postaux,
        sci.first_sci_date,
        f.ca_total, f.resultat_net_total, f.n_companies_avec_bilan_recent,
        -- Fix #2 : 2 LEFT JOIN hash (sk_pn/sk_np) au lieu d'EXISTS ILIKE wildcard
        (sk_pn.name_key IS NOT NULL OR sk_np.name_key IS NOT NULL) AS is_sanctionne,
        o.has_linkedin, o.has_github, o.has_any_social,
        o.n_linkedin, o.n_github, o.n_twitter, o.n_total_social,
        o.denomination_main_company   AS osint_main_deno,
        o.last_scanned_at             AS osint_scanned_at
    FROM base b
    LEFT JOIN finances f ON f.person_uid = b.person_uid
    LEFT JOIN sci       ON sci.nom_key = b.nom_key AND sci.prenom_key = b.prenom_key AND sci.dn_key = b.dn_key
    LEFT JOIN osint o   ON o.nom_key = b.nom_key AND o.dn_key = b.dn_key AND b.prenom = ANY (o.prenoms)
    LEFT JOIN sanctions_keys sk_pn ON sk_pn.name_key = b.name_key_pn
    LEFT JOIN sanctions_keys sk_np ON sk_np.name_key = b.name_key_np
    ORDER BY b.person_uid, o.n_total_social DESC NULLS LAST   -- 1 row/personne, garde le match OSINT le plus riche
)
SELECT
    person_uid, nom, prenom, date_naissance, age_2026,
    sirens_mandats, denominations, formes_juridiques, roles,
    n_mandats_actifs, n_mandats_total, is_multi_mandat,
    first_mandat_date, last_mandat_date,
    n_sci, total_capital_sci, sci_denominations, sci_code_postaux, first_sci_date,
    n_companies, n_companies_avec_bilan_recent, ca_total, resultat_net_total,
    is_sanctionne,
    has_linkedin, has_github, has_any_social,
    n_linkedin, n_github, n_twitter, n_total_social,
    osint_main_deno, osint_scanned_at,
    LEAST(100,
        (CASE WHEN n_mandats_actifs >= 10 THEN 10 ELSE 0 END) +
        (CASE WHEN n_sci >= 2 THEN 20 ELSE 0 END) +
        LEAST(15, COALESCE(ca_total, 0) / 10000000.0)::int +
        (CASE WHEN n_total_social >= 3 THEN 5 ELSE 0 END) -
        (CASE WHEN is_sanctionne THEN 20 ELSE 0 END)
    )::int AS pro_ma_score,
    now() AS materialized_at
FROM enriched;

CREATE INDEX dirigeants_360_nom_prenom_dn_idx   ON silver.dirigeants_360 (nom, prenom, date_naissance);
CREATE INDEX dirigeants_360_pro_ma_score_idx    ON silver.dirigeants_360 (pro_ma_score DESC);
CREATE INDEX dirigeants_360_n_mandats_idx       ON silver.dirigeants_360 (n_mandats_actifs DESC);
CREATE INDEX dirigeants_360_capital_sci_idx     ON silver.dirigeants_360 (total_capital_sci DESC);
CREATE INDEX dirigeants_360_sanctionne_idx      ON silver.dirigeants_360 (is_sanctionne) WHERE is_sanctionne = true;
CREATE INDEX dirigeants_360_sirens_gin_idx      ON silver.dirigeants_360 USING gin (sirens_mandats);
CREATE INDEX dirigeants_360_nom_idx             ON silver.dirigeants_360 (nom);
