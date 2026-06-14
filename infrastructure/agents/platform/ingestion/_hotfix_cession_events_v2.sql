-- cession_events v2 : parse le jugement BODACC (nature/famille/date) + statut M&A.
-- Regex sur le JSON-string (robuste vs cast jsonb qui plante sur strings invalides).
DROP MATERIALIZED VIEW IF EXISTS silver.cession_events;

CREATE MATERIALIZED VIEW silver.cession_events AS
WITH bodacc_cession AS (
  SELECT
    b.annonce_id,
    b.date_publication AS date_parution,
    NULLIF(regexp_replace(split_part(b.payload->>'registre', ',', -1), '[^0-9]', '', 'g'), '') AS siren_extr,
    b.tribunal,
    b.departement,
    b.ville,
    b.familleavis_lib,
    b.payload->>'jugement' AS jug,
    CASE
      WHEN b.familleavis_lib = 'Ventes et cessions' THEN 'vente_cession'
      WHEN b.familleavis_lib = 'Procédures collectives' THEN 'procedure_collective'
      WHEN b.familleavis_lib = 'Procédures de conciliation' THEN 'conciliation'
      WHEN b.familleavis_lib = 'Procédures de rétablissement professionnel' THEN 'retablissement'
      ELSE 'cession_autre'
    END AS type_cession,
    b.payload->>'denomination'           AS denomination,
    b.payload->>'forme_juridique'        AS forme_juridique,
    b.payload->>'numero_immatriculation' AS numero_immatriculation
  FROM bronze.bodacc_annonces_raw b
  WHERE b.familleavis_lib IN (
    'Ventes et cessions','Procédures collectives',
    'Procédures de conciliation','Procédures de rétablissement professionnel'
  )
),
parsed AS (
  SELECT *,
    substring(jug from '"nature":\s*"([^"]*)"')  AS procedure_nature,
    substring(jug from '"famille":\s*"([^"]*)"') AS procedure_famille,
    NULLIF(substring(jug from '"date":\s*"(\d{4}-\d{2}-\d{2})"'), '')::date AS jugement_date_p,
    substring(jug from '"complementJugement":\s*"([^"]*)"') AS jugement_complement
  FROM bodacc_cession
)
SELECT
  p.annonce_id,
  p.date_parution,
  CASE WHEN length(p.siren_extr) = 9 THEN p.siren_extr ELSE NULL END AS siren,
  p.tribunal, p.departement, p.ville,
  p.type_cession,
  p.denomination, p.forme_juridique, p.numero_immatriculation,
  p.procedure_nature,
  p.procedure_famille,
  p.jugement_date_p AS jugement_date,
  p.jugement_complement,
  -- Statut M&A actionnable dérivé de la nature du jugement
  CASE
    WHEN p.procedure_nature ILIKE '%plan de cession%'
      OR p.procedure_nature ILIKE '%plan%cession%'                        THEN 'plan_cession'
    WHEN p.procedure_nature ILIKE '%liquidation%'
      OR p.procedure_nature ILIKE '%cl%ture pour insuffisance%'           THEN 'terminal'
    WHEN p.procedure_nature ILIKE '%redressement%'
      OR p.procedure_nature ILIKE '%sauvegarde%'
      OR p.procedure_nature ILIKE '%plan%'                                THEN 'opportunite_reprise'
    WHEN p.procedure_nature ILIKE '%conversion%'
      OR p.procedure_nature ILIKE '%r%solution du plan%'                  THEN 'surveillance'
    WHEN p.procedure_nature ILIKE '%interdiction de g%rer%'
      OR p.procedure_nature ILIKE '%faillite personnelle%'               THEN 'dirigeant_sanctionne'
    WHEN p.procedure_nature ILIKE '%cl%ture%extinction%'                  THEN 'sauve'
    WHEN p.type_cession = 'vente_cession'                                 THEN 'vente_cession'
    ELSE 'autre'
  END AS procedure_statut_ma,
  (p.procedure_nature ILIKE '%plan de cession%' OR p.procedure_nature ILIKE '%plan%cession%') AS is_plan_cession,
  -- famille de clôture = procédure terminée
  (p.procedure_famille ILIKE '%cl%ture%' OR p.procedure_nature ILIKE '%cl%ture%') AS is_cloture,
  em.denomination     AS denomination_inpi,
  em.forme_juridique  AS forme_juridique_inpi,
  em.code_ape         AS code_ape_inpi,
  em.adresse_code_postal AS cp_inpi,
  (p.date_parution >= (now() - interval '90 days')) AS is_recent
FROM parsed p
LEFT JOIN gold.entreprises_master em
  ON length(p.siren_extr) = 9 AND em.siren = p.siren_extr
WHERE (CASE
      WHEN p.familleavis_lib = 'Ventes et cessions' THEN 'vente_cession'
      WHEN p.familleavis_lib = 'Procédures collectives' THEN 'procedure_collective'
      WHEN p.familleavis_lib = 'Procédures de conciliation' THEN 'conciliation'
      WHEN p.familleavis_lib = 'Procédures de rétablissement professionnel' THEN 'retablissement'
      ELSE 'cession_autre' END) <> 'cession_autre';

CREATE INDEX ON silver.cession_events (annonce_id);
CREATE INDEX ON silver.cession_events (siren, date_parution DESC);
CREATE INDEX ON silver.cession_events (type_cession);
CREATE INDEX ON silver.cession_events (procedure_statut_ma);
CREATE INDEX ON silver.cession_events (is_plan_cession) WHERE is_plan_cession = true;
CREATE INDEX ON silver.cession_events (date_parution DESC);
CREATE INDEX ON silver.cession_events (is_recent) WHERE is_recent = true;

ANALYZE silver.cession_events;
