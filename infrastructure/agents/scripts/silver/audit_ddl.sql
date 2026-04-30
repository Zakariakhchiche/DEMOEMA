-- Audit tables pour la silver layer
-- Tracks: silver spec versions (LLM-generated SQL), refresh runs, staleness
SET statement_timeout = 0;

CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS silver;

-- Histoire des SQL générés par le LLM pour chaque silver table
CREATE TABLE IF NOT EXISTS audit.silver_specs_versions (
    version_uid       text PRIMARY KEY,             -- sha1(silver_name|sql|generated_at)
    silver_name       varchar(128) NOT NULL,        -- ex: 'silver.inpi_comptes'
    spec_yaml         text NOT NULL,                -- YAML source spec
    generated_sql     text NOT NULL,                -- CREATE MATERIALIZED VIEW AS ...
    generator         varchar(32) NOT NULL,         -- 'codegen_llm' | 'manual' | 'template'
    llm_model         varchar(64),                  -- ex: 'qwen2.5-coder:32b'
    llm_feedback      text,                         -- error from previous attempt (if retry)
    validation_status varchar(16) NOT NULL,         -- 'ok' | 'invalid' | 'dangerous'
    validation_msg    text,
    applied           boolean NOT NULL DEFAULT false,
    generated_at      timestamptz NOT NULL DEFAULT now(),
    applied_at        timestamptz
);
CREATE INDEX IF NOT EXISTS idx_silver_specs_name  ON audit.silver_specs_versions(silver_name);
CREATE INDEX IF NOT EXISTS idx_silver_specs_applied ON audit.silver_specs_versions(silver_name, applied_at DESC);

-- Tool-calling audit (codegen_tools.py)
ALTER TABLE audit.silver_specs_versions
    ADD COLUMN IF NOT EXISTS tool_calls jsonb;
ALTER TABLE audit.silver_specs_versions
    ADD COLUMN IF NOT EXISTS tool_iterations int;

-- Log de chaque refresh MATERIALIZED VIEW
CREATE TABLE IF NOT EXISTS audit.silver_runs (
    run_uid          text PRIMARY KEY,
    silver_name      varchar(128) NOT NULL,
    refresh_start    timestamptz NOT NULL DEFAULT now(),
    refresh_end      timestamptz,
    duration_ms      int,
    rows_before      bigint,
    rows_after       bigint,
    delta_rows       bigint,                         -- rows_after - rows_before
    delta_pct        numeric(6,2),                   -- variation %
    status           varchar(16) NOT NULL,           -- 'running' | 'ok' | 'failed' | 'skipped'
    error            text,
    trigger_source   varchar(32)                     -- 'scheduler' | 'manual' | 'maintainer'
);
CREATE INDEX IF NOT EXISTS idx_silver_runs_name_date ON audit.silver_runs(silver_name, refresh_start DESC);
CREATE INDEX IF NOT EXISTS idx_silver_runs_status   ON audit.silver_runs(status) WHERE status != 'ok';

-- État courant agrégé par silver table (proxy freshness, facile à requêter)
CREATE TABLE IF NOT EXISTS audit.silver_freshness (
    silver_name        varchar(128) PRIMARY KEY,
    last_refresh_at    timestamptz,
    last_status        varchar(16),
    current_rows       bigint,
    sla_minutes        int,                          -- from spec
    is_stale           boolean,                      -- computed: now - last_refresh > sla_minutes
    last_delta_pct     numeric(6,2),
    consecutive_fails  int NOT NULL DEFAULT 0,
    parked             boolean NOT NULL DEFAULT false,
    parked_reason      text,
    updated_at         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_silver_fresh_stale ON audit.silver_freshness(is_stale) WHERE is_stale = true;
