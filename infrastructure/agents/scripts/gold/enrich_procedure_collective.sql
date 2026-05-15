-- Enrichit gold.entreprises_master avec le signal procédure collective BODACC
-- À exécuter après le refresh nightly de gold.entreprises_master (cron 03:30 UTC).
-- Idempotent : ALTER ADD COLUMN IF NOT EXISTS + UPDATE FROM CTE.
--
-- Pourquoi : la mémoire DEMOEMA n'a pas de source URSSAF privilèges en open
-- data. Le seul signal public exploitable pour détecter une entreprise en
-- difficulté financière (donc presque certainement avec une dette URSSAF) est
-- le flux BODACC procédures collectives, déjà ingéré dans bronze.bodacc_annonces_raw.
--
-- Bucket "active" = la dernière annonce BODACC pour ce SIREN est un jugement
-- d'ouverture (RJ/LJ/sauvegarde) ou une conversion, sans jugement de clôture
-- postérieur. Bucket "false" = procédure clôturée. NULL = pas de procédure.

BEGIN;

ALTER TABLE gold.entreprises_master
  ADD COLUMN IF NOT EXISTS has_procedure_collective_active BOOLEAN,
  ADD COLUMN IF NOT EXISTS last_procedure_date DATE,
  ADD COLUMN IF NOT EXISTS last_procedure_nature TEXT;

WITH latest_proc AS (
  SELECT DISTINCT ON (siren)
    siren,
    date_publication AS last_date,
    substring(payload->>'jugement' from '"nature":\s*"([^"]*)"') AS last_nature
  FROM bronze.bodacc_annonces_raw
  WHERE familleavis_lib = 'Procédures collectives'
    AND siren IS NOT NULL
    AND payload->>'jugement' <> ''
    AND date_publication >= '2020-01-01'
  ORDER BY siren, date_publication DESC NULLS LAST
)
UPDATE gold.entreprises_master gem
SET
  has_procedure_collective_active = CASE
    WHEN lp.last_nature ILIKE '%clôture%'
      OR lp.last_nature ILIKE 'Rétractation%'
      OR lp.last_nature ILIKE 'Jugement mettant fin%' THEN FALSE
    WHEN lp.last_nature ILIKE 'Jugement arrêtant%plan%'
      OR lp.last_nature ILIKE 'Jugement modifiant le plan%' THEN TRUE
    WHEN lp.last_nature ILIKE '%liquidation%'
      OR lp.last_nature ILIKE '%redressement%'
      OR lp.last_nature ILIKE '%sauvegarde%'
      OR lp.last_nature ILIKE 'Jugement d''ouverture%' THEN TRUE
    ELSE NULL
  END,
  last_procedure_date = lp.last_date,
  last_procedure_nature = lp.last_nature
FROM latest_proc lp
WHERE gem.siren::text = lp.siren::text;

CREATE INDEX IF NOT EXISTS entreprises_master_procedure_active_idx
  ON gold.entreprises_master (has_procedure_collective_active)
  WHERE has_procedure_collective_active = TRUE;

CREATE INDEX IF NOT EXISTS entreprises_master_procedure_date_idx
  ON gold.entreprises_master (last_procedure_date DESC)
  WHERE last_procedure_date IS NOT NULL;

COMMIT;
