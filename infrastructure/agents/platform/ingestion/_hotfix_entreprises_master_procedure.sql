-- Fix drift : ajoute à gold.entreprises_master les colonnes procédure attendues
-- par le backend (réseau red-flags, NetworkGraphView) mais inexistantes →
-- has_procedure_collective_active / last_procedure_nature / last_procedure_date.
-- Source : silver.cession_events (dernier jugement par siren).
ALTER TABLE gold.entreprises_master
  ADD COLUMN IF NOT EXISTS has_procedure_collective_active boolean,
  ADD COLUMN IF NOT EXISTS last_procedure_nature text,
  ADD COLUMN IF NOT EXISTS last_procedure_date date;

WITH latest_proc AS (
  SELECT DISTINCT ON (siren)
         siren, procedure_nature, is_cloture,
         COALESCE(jugement_date, date_parution) AS proc_date
  FROM silver.cession_events
  WHERE siren IS NOT NULL
    AND type_cession IN ('procedure_collective','conciliation','retablissement')
  ORDER BY siren, COALESCE(jugement_date, date_parution) DESC NULLS LAST
)
UPDATE gold.entreprises_master em
SET last_procedure_nature = lp.procedure_nature,
    last_procedure_date = lp.proc_date,
    has_procedure_collective_active =
      (lp.proc_date > now()::date - interval '36 months' AND NOT COALESCE(lp.is_cloture, false))
FROM latest_proc lp
WHERE lp.siren = em.siren;

-- index pour le réseau red-flags (filtre has_procedure_collective_active)
CREATE INDEX IF NOT EXISTS entreprises_master_proc_active_idx
  ON gold.entreprises_master (has_procedure_collective_active)
  WHERE has_procedure_collective_active = true;
