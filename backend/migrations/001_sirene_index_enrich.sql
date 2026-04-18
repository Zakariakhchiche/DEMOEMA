-- Migration 001 — Colonnes enrichissement EdRCF 6.0
-- À exécuter dans le SQL Editor de Supabase (dashboard → SQL Editor → New query)
-- Idempotent : ne plante pas si les colonnes existent déjà

ALTER TABLE sirene_index
  ADD COLUMN IF NOT EXISTS adresse           TEXT,
  ADD COLUMN IF NOT EXISTS code_postal       VARCHAR(5),
  ADD COLUMN IF NOT EXISTS ville             TEXT,
  ADD COLUMN IF NOT EXISTS site_web          TEXT,
  ADD COLUMN IF NOT EXISTS telephone         VARCHAR(20),
  ADD COLUMN IF NOT EXISTS linkedin_url      TEXT,
  ADD COLUMN IF NOT EXISTS email_domaine     TEXT,
  ADD COLUMN IF NOT EXISTS nom_dirigeant     TEXT,
  ADD COLUMN IF NOT EXISTS qualite_dirigeant TEXT,
  ADD COLUMN IF NOT EXISTS annee_naissance   SMALLINT,
  ADD COLUMN IF NOT EXISTS chiffre_affaires  BIGINT,
  ADD COLUMN IF NOT EXISTS resultat_net      BIGINT;

-- Index sur les colonnes les plus filtrées
CREATE INDEX IF NOT EXISTS idx_sirene_index_dept       ON sirene_index (dept);
CREATE INDEX IF NOT EXISTS idx_sirene_index_score      ON sirene_index (ma_score_estimate DESC);
CREATE INDEX IF NOT EXISTS idx_sirene_index_bodacc     ON sirene_index (bodacc_recent DESC);
CREATE INDEX IF NOT EXISTS idx_sirene_index_site_web   ON sirene_index (site_web) WHERE site_web IS NOT NULL;
