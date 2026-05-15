-- Perf index pour la query "top cibles M&A 75" (cibles par dept × score).
-- Identifié par QA agent : timeout >40s sur /api/datalake/cibles?dept=75.
-- Le plan d'exécution faisait un seq scan sur 411k rows × LEFT JOIN scoring_ma.
-- Idempotent : CREATE INDEX IF NOT EXISTS.

BEGIN;

-- Index principal : (adresse_dept, pro_ma_score DESC) partial sur actifs.
-- Couvre la query /cibles avec dept filter sans toucher au LEFT JOIN scoring_ma.
CREATE INDEX IF NOT EXISTS entreprises_master_dept_score_idx
  ON gold.entreprises_master (adresse_dept, pro_ma_score DESC NULLS LAST)
  WHERE insee_etat_administratif IS NULL OR insee_etat_administratif != 'F';

-- Index secondaire : (has_pro_ma, pro_ma_score DESC) partial sur ceux flaggés
-- pro M&A. Sert le dashboard top targets.
CREATE INDEX IF NOT EXISTS entreprises_master_proma_score_idx
  ON gold.entreprises_master (has_pro_ma, pro_ma_score DESC NULLS LAST)
  WHERE has_pro_ma = TRUE;

-- ANALYZE pour mettre à jour les stats du planner.
COMMIT;

ANALYZE gold.entreprises_master;
