-- ============================================================================
-- SaaS multi-tenant — schéma applicatif `app`
-- ============================================================================
-- SÉPARÉ du datalake (bronze/silver/gold = données de référence partagées,
-- read-only, INPI/SIRENE/BODACC). Le schéma `app` porte les données PAR CLIENT
-- (organisations, utilisateurs, watchlists, pipelines, recherches, usage).
--
-- Sécurité : isolation par org_id sur chaque table tenant. Row-Level Security
-- (RLS) activable ensuite ; en attendant, le backend filtre systématiquement
-- par org_id résolu depuis le token Clerk (cf. backend/auth/tenant.py).
--
-- Idempotent : CREATE ... IF NOT EXISTS partout. À appliquer sur la base
-- datalake (même Postgres pour démarrer ; DB dédiée recommandée à terme).
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS app;

-- Organisations (= tenants / espaces de travail facturables) -----------------
CREATE TABLE IF NOT EXISTS app.organizations (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_org_id  text UNIQUE,                       -- lien Clerk Organizations
    name          text NOT NULL,
    slug          text UNIQUE,
    plan          text NOT NULL DEFAULT 'trial',     -- trial | starter | pro | cabinet
    plan_status   text NOT NULL DEFAULT 'active',    -- active | past_due | canceled
    stripe_customer_id      text,                    -- Phase 2 billing
    stripe_subscription_id  text,
    trial_ends_at timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

-- Utilisateurs (miroir Clerk) ------------------------------------------------
CREATE TABLE IF NOT EXISTS app.users (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_user_id text UNIQUE NOT NULL,
    email         text,
    full_name     text,
    created_at    timestamptz NOT NULL DEFAULT now(),
    last_seen_at  timestamptz
);

-- Appartenance utilisateur ↔ organisation (+ rôle RBAC) ----------------------
CREATE TABLE IF NOT EXISTS app.memberships (
    org_id   uuid NOT NULL REFERENCES app.organizations(id) ON DELETE CASCADE,
    user_id  uuid NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    role     text NOT NULL DEFAULT 'member',         -- owner | admin | member
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (org_id, user_id)
);

-- ─── Données utilisateur (remplacent le localStorage) ───────────────────────

-- Watchlist : cibles suivies (siren) par org
CREATE TABLE IF NOT EXISTS app.watchlist_items (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id     uuid NOT NULL REFERENCES app.organizations(id) ON DELETE CASCADE,
    user_id    uuid REFERENCES app.users(id) ON DELETE SET NULL,
    siren      char(9) NOT NULL,
    denomination text,
    note       text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (org_id, siren)
);
CREATE INDEX IF NOT EXISTS watchlist_items_org_idx ON app.watchlist_items (org_id);

-- Recherches sauvegardées (filtres de sourcing réutilisables)
CREATE TABLE IF NOT EXISTS app.saved_searches (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id     uuid NOT NULL REFERENCES app.organizations(id) ON DELETE CASCADE,
    user_id    uuid REFERENCES app.users(id) ON DELETE SET NULL,
    name       text NOT NULL,
    params     jsonb NOT NULL DEFAULT '{}'::jsonb,    -- naf/dept/min_ca/effectif/distress…
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS saved_searches_org_idx ON app.saved_searches (org_id);

-- Pipeline deals (kanban d'origination)
CREATE TABLE IF NOT EXISTS app.pipeline_deals (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id     uuid NOT NULL REFERENCES app.organizations(id) ON DELETE CASCADE,
    siren      char(9),
    name       text NOT NULL,
    stage      text NOT NULL DEFAULT 'sourced',       -- sourced|contacted|nda|loi|dd|closing|won|lost
    side       text DEFAULT 'buy-side',               -- buy-side | sell-side
    owner_user_id uuid REFERENCES app.users(id) ON DELETE SET NULL,
    value_eur  numeric,
    next_action text,
    updated_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS pipeline_deals_org_idx ON app.pipeline_deals (org_id);

-- Conversations chat (persistées par org, remplace le localStorage)
CREATE TABLE IF NOT EXISTS app.conversations (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id     uuid NOT NULL REFERENCES app.organizations(id) ON DELETE CASCADE,
    user_id    uuid REFERENCES app.users(id) ON DELETE SET NULL,
    title      text,
    messages   jsonb NOT NULL DEFAULT '[]'::jsonb,
    updated_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS conversations_org_idx ON app.conversations (org_id, updated_at DESC);

-- ─── Usage / metering (base pour la facturation Phase 2) ────────────────────
CREATE TABLE IF NOT EXISTS app.usage_events (
    id         bigserial PRIMARY KEY,
    org_id     uuid NOT NULL REFERENCES app.organizations(id) ON DELETE CASCADE,
    user_id    uuid REFERENCES app.users(id) ON DELETE SET NULL,
    kind       text NOT NULL,                         -- llm_query | export | fiche_view | search
    cost_units numeric DEFAULT 1,                     -- ex tokens LLM, ou 1 par action
    metadata   jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS usage_events_org_time_idx ON app.usage_events (org_id, created_at DESC);
CREATE INDEX IF NOT EXISTS usage_events_kind_idx ON app.usage_events (org_id, kind, created_at DESC);

-- Quotas par plan (référence applicative, ajustable) -------------------------
CREATE TABLE IF NOT EXISTS app.plan_limits (
    plan            text PRIMARY KEY,
    max_seats       int,
    max_llm_per_day int,
    max_exports_per_month int,
    features        jsonb NOT NULL DEFAULT '{}'::jsonb
);
INSERT INTO app.plan_limits (plan, max_seats, max_llm_per_day, max_exports_per_month, features) VALUES
    ('trial',   1,  20,  5,   '{"graph": false, "export": true}'),
    ('starter', 3,  100, 50,  '{"graph": false, "export": true}'),
    ('pro',     10, 500, 500, '{"graph": true,  "export": true}'),
    ('cabinet', 50, 5000, 5000,'{"graph": true,  "export": true, "api": true}')
ON CONFLICT (plan) DO NOTHING;
