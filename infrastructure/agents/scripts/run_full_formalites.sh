#!/usr/bin/env bash
# Driver formalités : wait extract → 8-way parallel ingest → rebuild indexes.
set -u

LOG=/root/inpi_dumps/formalites_ingest.log
DIR=/root/inpi_dumps/formalites

exec > >(tee -a "$LOG") 2>&1

echo "[$(date -Iseconds)] === waiting for formalites unzip ==="
while [ ! -f /root/inpi_dumps/.formalites_extract_done ]; do sleep 20; done
N_FILES=$(ls "$DIR"/stock_*.json 2>/dev/null | wc -l)
echo "[$(date -Iseconds)] extract done — $N_FILES files ready"

echo "[$(date -Iseconds)] === launching 8-way parallel ingest ==="
T0=$(date +%s)

docker exec demomea-agents-platform bash -c '
  source <(python3 -c "from config import settings; print(f\"export DSN={settings.database_url}\")")
  ls /inpi_dumps/formalites/stock_*.json | xargs -P 8 -I{} python3 /tmp/ingest_formalites_fast.py {}
'

T1=$(date +%s)
DUR=$((T1-T0))
echo "[$(date -Iseconds)] === ingest done in ${DUR}s ==="

echo "[$(date -Iseconds)] === rebuilding indexes (CONCURRENTLY) ==="
for idx in \
  "idx_f_ent_forme_jur ON bronze.inpi_formalites_entreprises(forme_juridique)" \
  "idx_f_ent_type_personne ON bronze.inpi_formalites_entreprises(type_personne)" \
  "idx_f_ent_date_immat ON bronze.inpi_formalites_entreprises(date_immatriculation DESC)" \
  "idx_f_ent_code_ape ON bronze.inpi_formalites_entreprises(code_ape)" \
  "idx_f_ent_cp ON bronze.inpi_formalites_entreprises(adresse_code_postal)" \
  "idx_f_etab_siret ON bronze.inpi_formalites_etablissements(siret)" \
  "idx_f_etab_principal ON bronze.inpi_formalites_etablissements(is_principal) WHERE is_principal = true" \
  "idx_f_etab_cp ON bronze.inpi_formalites_etablissements(adresse_code_postal)" \
  "idx_f_etab_formality ON bronze.inpi_formalites_etablissements(formality_id)" \
  "idx_f_act_code_ape ON bronze.inpi_formalites_activites(code_ape)" \
  "idx_f_act_principal ON bronze.inpi_formalites_activites(indicateur_principal) WHERE indicateur_principal = true" \
  "idx_f_act_etab ON bronze.inpi_formalites_activites(etablissement_uid)" \
  "idx_f_pers_entreprise_siren ON bronze.inpi_formalites_personnes(entreprise_siren) WHERE entreprise_siren IS NOT NULL" \
  "idx_f_pers_nom_prenom ON bronze.inpi_formalites_personnes(individu_nom, (individu_prenoms[1]))" \
  "idx_f_pers_dob ON bronze.inpi_formalites_personnes(individu_date_naissance)" \
  "idx_f_pers_role ON bronze.inpi_formalites_personnes(role_entreprise)" \
  "idx_f_pers_type ON bronze.inpi_formalites_personnes(type_de_personne)" \
  "idx_f_obs_date ON bronze.inpi_formalites_observations(date_observation DESC)" \
  "idx_f_hist_date ON bronze.inpi_formalites_historique(date_integration DESC)"
do
  name="${idx%% *}"
  echo "[$(date -Iseconds)] building $name"
  docker exec demomea-datalake-db /usr/local/bin/psql -U postgres -d datalake -c \
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS $idx;" 2>&1
done

echo "[$(date -Iseconds)] === ALL DONE ==="
docker exec demomea-datalake-db /usr/local/bin/psql -U postgres -d datalake -c "
  SELECT 'entreprises' AS t, count(*) FROM bronze.inpi_formalites_entreprises
  UNION ALL SELECT 'etablissements', count(*) FROM bronze.inpi_formalites_etablissements
  UNION ALL SELECT 'activites', count(*) FROM bronze.inpi_formalites_activites
  UNION ALL SELECT 'personnes', count(*) FROM bronze.inpi_formalites_personnes
  UNION ALL SELECT 'observations', count(*) FROM bronze.inpi_formalites_observations
  UNION ALL SELECT 'historique', count(*) FROM bronze.inpi_formalites_historique
  UNION ALL SELECT 'inscriptions_offices', count(*) FROM bronze.inpi_formalites_inscriptions_offices;
"
