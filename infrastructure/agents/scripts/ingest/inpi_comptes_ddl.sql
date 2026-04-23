-- Bronze tables for INPI RNE comptes annuels — FTP dump ingestion
-- Design: normalize key fields for fast queries, keep full payload JSONB for future-proofing.

CREATE TABLE IF NOT EXISTS bronze.inpi_comptes_depots (
    depot_id         text PRIMARY KEY,
    siren            char(9),
    denomination     text,
    date_depot       date,
    date_cloture     date,
    num_chrono       text,
    confidentiality  varchar(16),
    type_bilan       varchar(4),
    deleted          boolean DEFAULT false,
    updated_at_src   timestamptz,
    ingested_at      timestamptz NOT NULL DEFAULT now(),
    payload          jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_depots_siren        ON bronze.inpi_comptes_depots(siren);
CREATE INDEX IF NOT EXISTS idx_depots_date_cloture ON bronze.inpi_comptes_depots(date_cloture DESC);
CREATE INDEX IF NOT EXISTS idx_depots_type_bilan   ON bronze.inpi_comptes_depots(type_bilan);

CREATE TABLE IF NOT EXISTS bronze.inpi_comptes_identite (
    depot_id                 text PRIMARY KEY,
    siren                    char(9),
    date_cloture             date,
    date_cloture_n_moins_1   date,
    code_greffe              varchar(8),
    num_depot                varchar(16),
    num_gestion              varchar(32),
    code_activite            varchar(8),
    duree_exercice_n         int,
    duree_exercice_n_moins_1 int,
    code_saisie              varchar(4),
    code_type_bilan          varchar(4),
    code_devise              char(3),
    code_origine_devise      varchar(4),
    code_confidentialite     varchar(4),
    adresse                  text
);
CREATE INDEX IF NOT EXISTS idx_identite_siren         ON bronze.inpi_comptes_identite(siren);
CREATE INDEX IF NOT EXISTS idx_identite_code_activite ON bronze.inpi_comptes_identite(code_activite);

CREATE TABLE IF NOT EXISTS bronze.inpi_comptes_liasses (
    depot_id      text NOT NULL,
    siren         char(9),
    date_cloture  date,
    page_num      smallint NOT NULL,
    code          varchar(8) NOT NULL,
    m1            numeric,
    m2            numeric,
    m3            numeric,
    m4            numeric,
    PRIMARY KEY (depot_id, page_num, code)
);
CREATE INDEX IF NOT EXISTS idx_liasses_siren_code ON bronze.inpi_comptes_liasses(siren, code);
CREATE INDEX IF NOT EXISTS idx_liasses_code       ON bronze.inpi_comptes_liasses(code);
