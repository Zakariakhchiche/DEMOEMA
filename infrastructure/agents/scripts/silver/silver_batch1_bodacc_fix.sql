-- Rebuild silver.bodacc_annonces with corrected structure
SET statement_timeout = 0;

DROP MATERIALIZED VIEW IF EXISTS silver.bodacc_annonces;
CREATE MATERIALIZED VIEW silver.bodacc_annonces AS
SELECT
  -- id is prefixed with Unicode BOM (﻿) in this dump — use COALESCE
  COALESCE(payload->>'id', payload->>E'﻿id') AS annonce_id,
  payload->>'parution' AS parution_id,
  payload->>'numeroannonce' AS numero_annonce,
  (NULLIF(payload->>'dateparution', ''))::date AS date_parution,
  payload->>'numerodepartement' AS code_dept,
  payload->>'departement_nom_officiel' AS departement,
  payload->>'region_code' AS code_region,
  payload->>'region_nom_officiel' AS region,
  payload->>'tribunal' AS tribunal,
  payload->>'ville' AS ville,
  -- SIREN extracted from registre field (format "414 464 099,414464099")
  CASE
    WHEN payload->>'registre' ~ '\d{9}'
    THEN regexp_replace(split_part(payload->>'registre', ',', -1), '[^0-9]', '', 'g')
    ELSE NULL
  END AS siren,
  NULLIF(payload->>'commercant', '') AS commercant,
  payload->>'typeavis' AS typeavis_code,
  NULLIF(payload->>'typeavis_lib', '') AS typeavis_lib,
  payload->>'familleavis' AS familleavis_code,
  NULLIF(payload->>'familleavis_lib', '') AS familleavis_lib,
  -- Classification dérivée (corrigée: 'dpc' = Dépôts comptes, 'procol' = Procédures collectives)
  CASE
    WHEN payload->>'familleavis' = 'procol' OR payload->>'familleavis_lib' ILIKE '%procédure%collective%' THEN 'procedure_collective'
    WHEN payload->>'familleavis' = 'dpc' OR payload->>'familleavis_lib' ILIKE '%comptes%' THEN 'depot_comptes'
    WHEN payload->>'familleavis' = 'cre' OR payload->>'familleavis_lib' ILIKE '%créations%' THEN 'creation'
    WHEN payload->>'familleavis' = 'rad' OR payload->>'familleavis_lib' ILIKE '%radiation%' THEN 'radiation'
    WHEN payload->>'familleavis' = 'mod' OR payload->>'familleavis_lib' ILIKE '%modification%' THEN 'modification'
    WHEN payload->>'familleavis' = 'imm' THEN 'immatriculation'
    WHEN payload->>'familleavis' = 'vente' OR payload->>'typeavis_lib' ILIKE '%vente%' OR payload->>'typeavis_lib' ILIKE '%cession%' THEN 'vente_cession'
    ELSE 'autre'
  END AS type_derivé,
  -- Extract depot/jugement nested JSON-as-string (BODACC stores them as strings!)
  CASE
    WHEN payload->>'depot' != '' THEN (payload->>'depot')::jsonb
    ELSE NULL
  END AS depot_details,
  CASE
    WHEN payload->>'jugement' != '' THEN (payload->>'jugement')::jsonb
    ELSE NULL
  END AS jugement_details,
  CASE
    WHEN payload->>'listepersonnes' != '' THEN (payload->>'listepersonnes')::jsonb
    ELSE NULL
  END AS listepersonnes,
  payload->>'url_complete' AS url_source,
  payload AS payload
FROM bronze.bodacc_annonces_raw
WHERE payload IS NOT NULL;

CREATE INDEX ON silver.bodacc_annonces(siren);
CREATE INDEX ON silver.bodacc_annonces(date_parution DESC);
CREATE INDEX ON silver.bodacc_annonces(type_derivé);
CREATE INDEX ON silver.bodacc_annonces(siren, date_parution DESC);
CREATE INDEX ON silver.bodacc_annonces(familleavis_code);
