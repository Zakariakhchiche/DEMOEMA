# Origin → SaaS — plan & avancement

Transformation de l'outil M&A mono-tenant en SaaS multi-tenant. Cible : large
(cabinets M&A, fonds, experts-comptables/CGP, M&A interne) → on construit générique.

## ⚠️ Phase 0 — Conformité RGPD (BLOQUANT avant commercialisation)
Origin agrège des **données personnelles de personnes physiques françaises**
(dirigeants : nom, âge, **emails/OSINT**, patrimoine SCI, sanctions, PEP).
Commercialiser = exposition CNIL/RGPD. À cadrer (idéalement avec un avocat) :
- Base légale (intérêt légitime prospection B2B) + balance test.
- Registre des traitements, mentions d'information, droit d'opposition/effacement.
- DPA avec les clients (sous-traitance).
- **Minimisation** : les emails OSINT et le flag PEP sont les plus sensibles.

## Phase 1 — Auth + multi-tenant  ← EN COURS
- **Auth : Clerk** (free tier, déjà utilisé sur PhanteraTN). Organizations Clerk = tenants.
- Schéma `app` séparé du datalake → `infrastructure/migrations/app_schema_001.sql`
  (organizations, users, memberships, watchlist, saved_searches, pipeline_deals,
  conversations, usage_events, plan_limits).
- Backend : `backend/auth/tenant.py` (vérif JWT Clerk + upsert user/org +
  dépendance `get_tenant_context`). **Feature flag `AUTH_ENABLED`** → off = prod
  actuelle inchangée tant que Clerk n'est pas branché.
- Migrer les données USER du localStorage (watchlist, conversations) vers `app.*`.

### 👉 Action requise de ta part (Zak)
1. Créer une app **Clerk** (gratuit) : https://clerk.com → activer **Organizations**.
2. Me fournir (via `! echo ... >> .env` ou secret) :
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
   - `CLERK_SECRET_KEY`
   - `CLERK_JWKS_URL` (https://<ton-app>.clerk.accounts.dev/.well-known/jwks.json)
   - `CLERK_ISSUER` (https://<ton-app>.clerk.accounts.dev)
3. Valider l'application du schéma `app` sur la base de prod (additif, ne touche
   pas au datalake).

Une fois ça reçu : je branche ClerkProvider + middleware Next.js, les pages
sign-in/up, je passe `AUTH_ENABLED=true`, et je migre watchlist/conversations en DB.

## Phase 2 — Billing + quotas (Stripe)
- Plans trial/starter/pro/cabinet (cf. `app.plan_limits`).
- Metering via `app.usage_events` (coût LLM DeepSeek, exports, fiches).
- Webhooks Stripe → `organizations.plan` / `plan_status`. Rate-limit + gating par plan.

## Phase 3 — Infra prod scalable
- Postgres managé (datalake lourd), Neo4j Aura, app conteneurisée scalable,
  Sentry, backups, staging, CI/CD.

## Phase 4 — Go-to-market
- Onboarding self-serve (signup + trial), pricing page, docs, support, statut.
