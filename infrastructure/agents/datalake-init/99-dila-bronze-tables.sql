-- DILA OpenData bronze tables — créées idempotemment au boot via docker-entrypoint-initdb.d
-- ou exécutables manuellement via :
--   docker exec demomea-datalake-db psql -U postgres -d datalake \
--     -f /docker-entrypoint-initdb.d/99-dila-bronze-tables.sql
--
-- Fichier numéroté 99 pour passer APRÈS 01-schema.sql qui crée le schema 'bronze'.

-- ─── Tables DILA juri (déjà existantes via 01-schema.sql, gardées pour ref) ───
-- bronze.judilibre_decisions_raw  → CASS (Cour de cassation)
-- bronze.juri_capp_raw            → CAPP (Cours d'appel)
-- bronze.juri_jade_raw            → JADE (Conseil d'État admin)
-- bronze.juri_constit_raw         → CONSTIT (Conseil constitutionnel)
-- bronze.legifrance_textes_raw    → LEGI (codes & textes consolidés)

-- ─── AMF décisions/sanctions (DILA bulk, distinct des amf_geco/bdif/listes_noires) ───
CREATE TABLE IF NOT EXISTS bronze.amf_dila_raw (
    decision_id   varchar(128) PRIMARY KEY,
    payload       jsonb        NOT NULL,
    ingested_at   timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_amf_dila_raw_ingested ON bronze.amf_dila_raw(ingested_at DESC);

-- ─── BALO — Bulletin des Annonces Légales Obligatoires (sociétés cotées) ───
CREATE TABLE IF NOT EXISTS bronze.balo_announcements_raw (
    announcement_id varchar(128) PRIMARY KEY,
    payload         jsonb        NOT NULL,
    ingested_at     timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_balo_announcements_ingested ON bronze.balo_announcements_raw(ingested_at DESC);

-- ─── JORF — Journal Officiel République Française ───
CREATE TABLE IF NOT EXISTS bronze.jorf_textes_raw (
    text_id      varchar(128) PRIMARY KEY,
    payload      jsonb        NOT NULL,
    ingested_at  timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_jorf_textes_ingested ON bronze.jorf_textes_raw(ingested_at DESC);

-- ─── KALI — Conventions collectives nationales ───
CREATE TABLE IF NOT EXISTS bronze.kali_ccn_raw (
    convention_id varchar(128) PRIMARY KEY,
    payload       jsonb        NOT NULL,
    ingested_at   timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_kali_ccn_ingested ON bronze.kali_ccn_raw(ingested_at DESC);

-- ─── DOLE — Dossiers législatifs (parcours d'une loi) ───
CREATE TABLE IF NOT EXISTS bronze.dole_dossiers_raw (
    dossier_id   varchar(128) PRIMARY KEY,
    payload      jsonb        NOT NULL,
    ingested_at  timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_dole_dossiers_ingested ON bronze.dole_dossiers_raw(ingested_at DESC);

-- ─── BOCC — Bulletin Officiel Conventions Collectives (avenants annuels) ───
CREATE TABLE IF NOT EXISTS bronze.bocc_avenants_raw (
    bocc_id      varchar(128) PRIMARY KEY,
    payload      jsonb        NOT NULL,
    ingested_at  timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_bocc_avenants_ingested ON bronze.bocc_avenants_raw(ingested_at DESC);

-- ─── CNIL sanctions (table manquante détectée pendant le full_backfill) ───
CREATE TABLE IF NOT EXISTS bronze.cnil_sanctions_raw (
    sanction_id  varchar(128) PRIMARY KEY,
    payload      jsonb        NOT NULL,
    ingested_at  timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cnil_sanctions_ingested ON bronze.cnil_sanctions_raw(ingested_at DESC);
