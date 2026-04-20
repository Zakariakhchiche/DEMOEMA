-- Migration : completeness tracking + anti-loop guards + audit trail enrichi
-- Safe à rejouer (IF NOT EXISTS partout)

ALTER TABLE audit.source_freshness
  ADD COLUMN IF NOT EXISTS upstream_row_count     BIGINT,
  ADD COLUMN IF NOT EXISTS upstream_checked_at    TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS completeness_pct       NUMERIC(5,2),
  ADD COLUMN IF NOT EXISTS retry_count            INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_regen_attempt_at  TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS parked_at              TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS parked_reason          TEXT;

-- Élargir la contrainte de status
ALTER TABLE audit.source_freshness DROP CONSTRAINT IF EXISTS source_freshness_status_check;
ALTER TABLE audit.source_freshness
  ADD CONSTRAINT source_freshness_status_check
  CHECK (status IN ('ok','ok_empty','degraded','failed','incomplete','parked','never_run'));

-- Index pour la requête du Maintainer (scan rapide des candidats à régénérer)
CREATE INDEX IF NOT EXISTS idx_freshness_maintainer
  ON audit.source_freshness(status, retry_count, last_regen_attempt_at)
  WHERE status NOT IN ('parked','ok_empty');

COMMENT ON COLUMN audit.source_freshness.upstream_row_count IS 'Total rows disponibles côté source (amont). NULL = non supporté ou non encore vérifié.';
COMMENT ON COLUMN audit.source_freshness.completeness_pct    IS 'total_rows / upstream_row_count * 100. NULL si upstream inconnu.';
COMMENT ON COLUMN audit.source_freshness.retry_count         IS 'Tentatives consécutives de régénération. Reset à 0 dès que rows>0. Après 3 → parked.';
COMMENT ON COLUMN audit.source_freshness.parked_at           IS 'Source retirée de la boucle auto (intervention humaine requise).';
