-- DDL for the 2 missing bronze tables that fetchers reference but never got created.
-- Matches the shape of existing bronze.*_raw tables (record_id/key TEXT PK, payload JSONB).

CREATE TABLE IF NOT EXISTS bronze.api_cadastre_ign_raw (
    record_id    TEXT        PRIMARY KEY,
    payload      JSONB       NOT NULL,
    ingested_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_api_cadastre_ign_raw_ingested_at
    ON bronze.api_cadastre_ign_raw (ingested_at DESC);


CREATE TABLE IF NOT EXISTS bronze.urssaf_opendata_raw (
    record_id    TEXT        PRIMARY KEY,
    payload      JSONB       NOT NULL,
    ingested_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_urssaf_opendata_raw_ingested_at
    ON bronze.urssaf_opendata_raw (ingested_at DESC);
