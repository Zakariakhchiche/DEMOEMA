-- SILVER BATCH 1: inpi_comptes + bodacc_annonces + inpi_dirigeants
-- Build time estimate: 10-20 min (gros GROUP BY sur 332M liasses)

SET statement_timeout = 0;  -- pas de timeout pour gros builds

-- ═══════════════════════════════════════════════════════════════════════
-- 1) silver.inpi_comptes — 1 row par dépôt (bilan), liasses aplaties en colonnes
-- ═══════════════════════════════════════════════════════════════════════
DROP MATERIALIZED VIEW IF EXISTS silver.inpi_comptes;
CREATE MATERIALIZED VIEW silver.inpi_comptes AS
SELECT
  d.depot_id,
  d.siren,
  d.denomination,
  d.date_cloture,
  d.date_depot,
  d.type_bilan,
  d.confidentiality,
  -- Compte de résultat (page 3, m1=FR, m2=export, m3=total N, m4=N-1)
  MAX(CASE WHEN l.code = 'FL' THEN COALESCE(l.m3, l.m1) END) AS ventes_marchandises,
  MAX(CASE WHEN l.code = 'FJ' THEN l.m1 END)                  AS ca_france,
  MAX(CASE WHEN l.code = 'FK' THEN l.m1 END)                  AS ca_export,
  MAX(CASE WHEN l.code = 'FR' THEN COALESCE(l.m3, l.m1) END)  AS ca_net,
  MAX(CASE WHEN l.code = 'HN' THEN COALESCE(l.m1, l.m3) END)  AS resultat_net,
  MAX(CASE WHEN l.code = 'HH' THEN COALESCE(l.m1, l.m3) END)  AS resultat_avant_impot,
  MAX(CASE WHEN l.code = 'GG' THEN COALESCE(l.m1, l.m3) END)  AS resultat_exploitation,
  -- Bilan actif (m3 = net N, m4 = net N-1)
  MAX(CASE WHEN l.code = 'CO' THEN l.m3 END)                  AS total_actif,
  MAX(CASE WHEN l.code = 'BJ' THEN l.m3 END)                  AS immo_incorporelles,
  MAX(CASE WHEN l.code = 'BX' THEN l.m3 END)                  AS immo_corporelles,
  MAX(CASE WHEN l.code = 'BZ' THEN l.m3 END)                  AS immo_financieres,
  MAX(CASE WHEN l.code = 'CJ' THEN l.m3 END)                  AS stocks,
  MAX(CASE WHEN l.code = 'CF' THEN l.m3 END)                  AS creances_clients,
  -- Bilan passif
  MAX(CASE WHEN l.code = 'DA' THEN COALESCE(l.m1, l.m3) END)  AS capital_social,
  MAX(CASE WHEN l.code = 'DL' THEN l.m3 END)                  AS capitaux_propres,
  MAX(CASE WHEN l.code = 'DR' THEN l.m3 END)                  AS total_passif,
  MAX(CASE WHEN l.code = 'DU' THEN l.m3 END)                  AS emprunts_dettes,
  -- Effectif + infos
  MAX(CASE WHEN l.code = 'YP' THEN l.m1 END)                  AS effectif_moyen,
  d.updated_at_src,
  count(l.code) AS n_liasses_lignes,
  now() AS materialized_at
FROM bronze.inpi_comptes_depots d
LEFT JOIN bronze.inpi_comptes_liasses l USING (depot_id)
GROUP BY d.depot_id, d.siren, d.denomination, d.date_cloture, d.date_depot,
         d.type_bilan, d.confidentiality, d.updated_at_src;

CREATE INDEX ON silver.inpi_comptes(siren);
CREATE INDEX ON silver.inpi_comptes(date_cloture DESC);
CREATE INDEX ON silver.inpi_comptes(siren, date_cloture DESC);


-- ═══════════════════════════════════════════════════════════════════════
-- 2) silver.bodacc_annonces — 29M annonces classifiées
-- ═══════════════════════════════════════════════════════════════════════
DROP MATERIALIZED VIEW IF EXISTS silver.bodacc_annonces;
CREATE MATERIALIZED VIEW silver.bodacc_annonces AS
SELECT
  payload->>'id' AS annonce_id,
  NULLIF(payload->>'registre', '') AS registre,
  NULLIF(payload->>'numeroannonce', '') AS numero_annonce,
  (NULLIF(payload->>'dateparution', ''))::date AS date_parution,
  NULLIF(payload->>'numerodepartement', '') AS code_dept,
  NULLIF(payload->>'departement_nom_officiel', '') AS departement,
  NULLIF(payload->>'tribunal', '') AS tribunal,
  NULLIF(payload#>>'{commercant,siren}', '') AS siren,
  NULLIF(payload#>>'{commercant,denomination}', '') AS denomination,
  NULLIF(payload->>'typeavis_lib', '') AS typeavis_lib,
  NULLIF(payload->>'familleavis_lib', '') AS familleavis_lib,
  -- Classification dérivée (simplifier le type)
  CASE
    WHEN payload->>'familleavis_lib' ILIKE '%procédure%collective%' THEN 'procedure_collective'
    WHEN payload->>'familleavis_lib' ILIKE '%cession%' OR payload->>'typeavis_lib' ILIKE '%cession%' THEN 'cession'
    WHEN payload->>'familleavis_lib' ILIKE '%dissolution%' OR payload->>'typeavis_lib' ILIKE '%dissolution%' THEN 'dissolution'
    WHEN payload->>'familleavis_lib' ILIKE '%créations%' OR payload->>'typeavis_lib' ILIKE '%création%' THEN 'creation'
    WHEN payload->>'familleavis_lib' ILIKE '%modification%' THEN 'modification'
    WHEN payload->>'familleavis_lib' ILIKE '%radiation%' THEN 'radiation'
    WHEN payload->>'typeavis_lib' ILIKE '%vente%' OR payload->>'typeavis_lib' ILIKE '%fonds%' THEN 'vente_fonds'
    ELSE 'autre'
  END AS type_derivé,
  payload AS payload
FROM bronze.bodacc_annonces_raw
WHERE payload->>'id' IS NOT NULL;

CREATE INDEX ON silver.bodacc_annonces(siren);
CREATE INDEX ON silver.bodacc_annonces(date_parution DESC);
CREATE INDEX ON silver.bodacc_annonces(type_derivé);
CREATE INDEX ON silver.bodacc_annonces(siren, date_parution DESC);


-- ═══════════════════════════════════════════════════════════════════════
-- 3) silver.inpi_dirigeants — 1 row par personne physique identifiée (GROUP BY identité)
-- ═══════════════════════════════════════════════════════════════════════
DROP MATERIALIZED VIEW IF EXISTS silver.inpi_dirigeants;
CREATE MATERIALIZED VIEW silver.inpi_dirigeants AS
SELECT
  upper(trim(p.individu_nom)) AS nom,
  COALESCE(upper(trim(p.individu_prenoms[1])), '') AS prenom,
  p.individu_date_naissance AS date_naissance,
  -- Agrégats de mandats
  count(DISTINCT p.siren) AS n_mandats_total,
  count(DISTINCT p.siren) FILTER (WHERE p.actif) AS n_mandats_actifs,
  array_agg(DISTINCT p.siren) AS sirens_mandats,
  array_agg(DISTINCT e.denomination) FILTER (WHERE e.denomination IS NOT NULL) AS denominations,
  array_agg(DISTINCT e.forme_juridique) FILTER (WHERE e.forme_juridique IS NOT NULL) AS formes_juridiques,
  -- SCI specific (repris de dirigeant_sci_patrimoine)
  count(DISTINCT e.siren) FILTER (WHERE e.forme_juridique LIKE '654%') AS n_sci,
  array_agg(DISTINCT e.siren) FILTER (WHERE e.forme_juridique LIKE '654%') AS sci_sirens,
  sum(e.montant_capital) FILTER (WHERE e.forme_juridique LIKE '654%') AS total_capital_sci,
  -- Proxy "pro M&A" : dirigeant avec 5+ mandats
  (count(DISTINCT p.siren) >= 5) AS is_multi_mandat,
  -- Rôles
  array_agg(DISTINCT p.role_entreprise) FILTER (WHERE p.role_entreprise IS NOT NULL) AS roles,
  -- Age en 2026 (si date naissance parsable en année)
  CASE
    WHEN p.individu_date_naissance ~ '^\d{4}'
    THEN 2026 - substring(p.individu_date_naissance, 1, 4)::int
    ELSE NULL
  END AS age_2026,
  -- Premier mandat (date immat min)
  min(e.date_immatriculation) AS first_mandat_date,
  max(e.date_immatriculation) AS last_mandat_date,
  now() AS materialized_at
FROM bronze.inpi_formalites_personnes p
LEFT JOIN bronze.inpi_formalites_entreprises e ON e.siren = p.siren
WHERE p.type_de_personne = 'INDIVIDU'
  AND p.individu_nom IS NOT NULL
  AND length(p.individu_nom) > 1
GROUP BY upper(trim(p.individu_nom)),
         COALESCE(upper(trim(p.individu_prenoms[1])), ''),
         p.individu_date_naissance;

CREATE INDEX ON silver.inpi_dirigeants(nom, prenom);
CREATE INDEX ON silver.inpi_dirigeants(date_naissance);
CREATE INDEX ON silver.inpi_dirigeants(n_mandats_actifs DESC);
CREATE INDEX ON silver.inpi_dirigeants(is_multi_mandat) WHERE is_multi_mandat = true;
CREATE INDEX ON silver.inpi_dirigeants USING gin(sirens_mandats);
