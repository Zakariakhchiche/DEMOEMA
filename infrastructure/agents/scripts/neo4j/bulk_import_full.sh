#!/usr/bin/env bash
# ============================================================================
# Neo4j FULL bulk import — toute la base 8M dirigeants + millions companies.
#
# Pipeline :
#   1. Export CSV depuis Postgres (Companies + Persons + IS_DIRIGEANT)
#   2. Stop Neo4j (offline pour neo4j-admin import)
#   3. neo4j-admin database import (x10 plus rapide que Cypher streaming)
#   4. Start Neo4j → indexes auto-build au 1er query
#
# Volumes attendus :
#   - companies.csv  : ~5M rows  (~ 1 GB)
#   - persons.csv    : ~8M rows  (~ 2 GB)
#   - is_dirigeant.csv : ~30M rows (~ 3 GB)
#
# Durée totale : ~30-60 min selon I/O VPS.
#
# Usage :
#   ./bulk_import_full.sh export    # juste export CSV
#   ./bulk_import_full.sh import    # juste import (CSV doivent exister)
#   ./bulk_import_full.sh full      # export + import + restart
# ============================================================================
set -euo pipefail

REPO_DIR="${REPO_DIR:-/root/DEMOEMA}"
EXPORT_DIR="/var/lib/neo4j-import"
DATALAKE_CONTAINER="demomea-datalake-db"
NEO4J_CONTAINER="demomea-neo4j"
DB_NAME="neo4j"  # default db name on Neo4j 5

red()    { printf "\033[31m%s\033[0m\n" "$*" >&2; }
green()  { printf "\033[32m%s\033[0m\n" "$*"; }
blue()   { printf "\033[34m%s\033[0m\n" "$*"; }

die() { red "ERROR: $*"; exit 1; }

derive_dsn() {
    local pwd_var
    pwd_var=$(grep -E '^DATALAKE_POSTGRES_ROOT_PASSWORD=' "${REPO_DIR}/.env" | head -1 | cut -d= -f2-)
    [ -n "$pwd_var" ] || die "DATALAKE_POSTGRES_ROOT_PASSWORD missing"
    echo "postgres://postgres:${pwd_var}@datalake-db:5432/datalake"
}

# ─── Phase A : Export CSV via psql COPY ────────────────────────────────────
do_export() {
    blue "[1/4] Export CSV depuis Postgres..."
    mkdir -p "$EXPORT_DIR"
    chmod 777 "$EXPORT_DIR"

    # Companies — toutes formes juridiques, tous capital. Filtre minimal :
    # actif, denomination NOT NULL.
    blue "  Exporting companies.csv..."
    docker exec -i "$DATALAKE_CONTAINER" psql -U postgres -d datalake -c "
SET statement_timeout = 0;
COPY (
  SELECT DISTINCT ON (siren)
    siren AS \"siren:ID(Company)\",
    coalesce(denomination, '') AS denomination,
    coalesce(forme_juridique, '') AS forme_juridique,
    coalesce(montant_capital, 0) AS \"capital:double\",
    coalesce(code_ape, '') AS code_ape,
    to_char(date_immatriculation, 'YYYY-MM-DD') AS date_immat,
    coalesce(adresse_code_postal, '') AS code_postal,
    'Company' AS \":LABEL\"
  FROM bronze.inpi_formalites_entreprises
  WHERE siren IS NOT NULL
    AND length(siren) = 9
    AND coalesce(denomination, '') != ''
  ORDER BY siren
) TO STDOUT CSV HEADER;
" > "$EXPORT_DIR/companies.csv"
    green "    $(wc -l < $EXPORT_DIR/companies.csv) lines"

    # Persons — depuis silver.inpi_dirigeants (8M rows), pré-agrégés.
    # uid = sha1(nom|prenom_trié|date_naissance) pour stable join avec is_dirigeant.csv
    blue "  Exporting persons.csv..."
    docker exec -i "$DATALAKE_CONTAINER" psql -U postgres -d datalake -c "
SET statement_timeout = 0;
COPY (
  SELECT
    md5(coalesce(nom,'')||'|'||coalesce(prenom,'')||'|'||coalesce(date_naissance,'')) AS \"uid:ID(Person)\",
    coalesce(nom, '') AS nom,
    coalesce(prenom, '') AS prenom,
    coalesce(prenom || ' ' || nom, '') AS full_name,
    coalesce(date_naissance, '') AS date_naissance,
    coalesce(age_2026, 0) AS \"age_2026:int\",
    coalesce(n_mandats_actifs, 0) AS \"n_mandats_actifs:int\",
    'Person' AS \":LABEL\"
  FROM silver.inpi_dirigeants
  WHERE nom IS NOT NULL
    AND length(nom) > 1
) TO STDOUT CSV HEADER;
" > "$EXPORT_DIR/persons.csv"
    green "    $(wc -l < $EXPORT_DIR/persons.csv) lines"

    # IS_DIRIGEANT — Person -[role]-> Company depuis bronze.inpi_formalites_personnes.
    # JOIN sur (nom, prenom, date_naissance) pour resolver le person_uid.
    blue "  Exporting is_dirigeant.csv..."
    docker exec -i "$DATALAKE_CONTAINER" psql -U postgres -d datalake -c "
SET statement_timeout = 0;
COPY (
  SELECT
    md5(coalesce(p.individu_nom,'')||'|'||coalesce(p.individu_prenoms[1],'')||'|'||coalesce(p.individu_date_naissance,'')) AS \":START_ID(Person)\",
    p.siren AS \":END_ID(Company)\",
    coalesce(p.individu_role, '') AS role,
    coalesce(p.actif, false) AS \"actif:boolean\",
    'IS_DIRIGEANT' AS \":TYPE\"
  FROM bronze.inpi_formalites_personnes p
  JOIN bronze.inpi_formalites_entreprises e ON e.siren = p.siren
  WHERE p.type_de_personne = 'INDIVIDU'
    AND p.individu_nom IS NOT NULL
    AND length(p.individu_nom) > 1
    AND p.siren IS NOT NULL
    AND length(p.siren) = 9
    AND coalesce(e.denomination, '') != ''
) TO STDOUT CSV HEADER;
" > "$EXPORT_DIR/is_dirigeant.csv"
    green "    $(wc -l < $EXPORT_DIR/is_dirigeant.csv) lines"

    blue "  Files in $EXPORT_DIR:"
    ls -lh "$EXPORT_DIR"/*.csv
}

# ─── Phase B : Stop Neo4j + neo4j-admin import + Start ────────────────────
do_import() {
    blue "[2/4] Stop Neo4j container..."
    docker stop "$NEO4J_CONTAINER" 2>&1 | tail -2

    blue "[3/4] neo4j-admin database import (offline, x10 faster than Cypher)..."

    # Wipe existing graph data (full replace strategy).
    # Note : data dir mount = neo4j-data volume.
    docker run --rm \
        -v demoema-agents_neo4j-data:/data \
        -v demoema-agents_neo4j-logs:/logs \
        -v "$EXPORT_DIR":/import:ro \
        --user 0:0 \
        neo4j:5-community \
        bash -c "
            rm -rf /data/databases/$DB_NAME /data/transactions/$DB_NAME 2>/dev/null
            neo4j-admin database import full \
                --overwrite-destination=true \
                --nodes=Company=/import/companies.csv \
                --nodes=Person=/import/persons.csv \
                --relationships=IS_DIRIGEANT=/import/is_dirigeant.csv \
                --skip-bad-relationships=true \
                --skip-duplicate-nodes=true \
                --multiline-fields=true \
                --high-parallel-io=on \
                --verbose \
                $DB_NAME
        " 2>&1 | tail -40

    blue "[4/4] Start Neo4j..."
    docker start "$NEO4J_CONTAINER" 2>&1 | tail -2
    green "Done. Wait ~60s for Neo4j to be healthy + indexes built."
    sleep 60

    # Apply schema (constraints + indexes) post-import
    docker exec "$NEO4J_CONTAINER" cypher-shell -u neo4j -p "${NEO4J_PASSWORD:-demoema_neo4j_pass}" "
        CREATE CONSTRAINT company_siren IF NOT EXISTS FOR (c:Company) REQUIRE c.siren IS UNIQUE;
        CREATE CONSTRAINT person_uid IF NOT EXISTS FOR (p:Person) REQUIRE p.uid IS UNIQUE;
        CREATE INDEX person_nom IF NOT EXISTS FOR (p:Person) ON (p.nom);
        CREATE INDEX person_full_name IF NOT EXISTS FOR (p:Person) ON (p.full_name);
        CREATE INDEX company_forme IF NOT EXISTS FOR (c:Company) ON (c.forme_juridique);
    " 2>&1 | tail -5

    docker exec "$NEO4J_CONTAINER" cypher-shell -u neo4j -p "${NEO4J_PASSWORD:-demoema_neo4j_pass}" "
        MATCH (c:Company) RETURN count(c) AS companies;
        MATCH (p:Person) RETURN count(p) AS persons;
        MATCH ()-[r:IS_DIRIGEANT]->() RETURN count(r) AS edges;
    " 2>&1 | tail -10
}

mode="${1:-help}"
case "$mode" in
    export) do_export ;;
    import) do_import ;;
    full) do_export; do_import ;;
    *) echo "Usage: $0 {export|import|full}" ;;
esac
