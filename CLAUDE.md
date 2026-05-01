# DEMOEMA — Instructions pour agents IA codeurs

Plateforme M&A propriétaire (origination + DD + scoring) sur stack FastAPI / Next.js 15 / Postgres datalake / Caddy / Docker, déployée sur VPS IONOS.

## Avant toute modification UI : lire `DESIGN.md`

Le fichier [`DESIGN.md`](./DESIGN.md) à la racine est la **source-of-truth** du système de design. Il contient :
- Tokens YAML normatifs (couleurs, typographie, spacing, rounded, composants)
- Classes CSS canoniques (`dem-glass`, `dem-btn`, `sheet-panel`, `score-halo`, etc.)
- Do's & Don'ts (anti-régression visuelle — cf. incident PR #11 où une refonte Bloomberg avait écrasé le glassmorphism existant)

**Règle dure** : ne jamais introduire de couleur, classe, ou composant UI hors `DESIGN.md` sans :
1. Vérifier que le besoin n'est pas déjà couvert par un token / composant existant.
2. Ajouter le nouveau token dans `DESIGN.md` ET dans `frontend/src/app/globals.css`.

**Validation** :
```bash
cd frontend && npm run lint:design
```
→ Lint structurel + check WCAG sur paires `textColor`/`backgroundColor`. Doit passer avant tout PR touchant l'UI.

## Stack en bref

- **Frontend** : `frontend/` — Next.js 15, React 19, Tailwind CSS v4, TypeScript strict. Hash routing (`#chat`, `#dashboard`, `#pipeline`, etc.). Composants design custom dans `frontend/src/components/dem/`.
- **Backend** : `backend/` — FastAPI 3.11, asyncpg, SSE streaming via `streamCopilot`. Endpoints `/api/datalake/*` et `/api/copilot/stream`.
- **Datalake** : Postgres 16 + materialized views `silver.*` / `gold.*`. Whitelist explicite dans `backend/datalake.py` (`GOLD_TABLES_WHITELIST`).
- **Deploy** : Docker Compose sur VPS `82-165-57-191.sslip.io`. Caddy reverse-proxy auto-TLS. Frontend + backend rebuild via `docker compose build && docker compose up -d`.

## Conventions code

- **Conventional Commits** : `feat(scope): ...`, `fix(scope): ...`, `chore(deps): ...`. Exemples : `feat(chat): ...`, `fix(fiche-dirigeant): ...`.
- **Pas de PR direct sur main** : feature branch + PR + merge. Les checks Vercel/Cloudflare Workers sont **legacy** (prod = IONOS), peuvent failer sans bloquer.
- **Tests TypeScript** : `node_modules/.bin/tsc --noEmit` doit passer sur les fichiers modifiés (les erreurs préexistantes dans `graph/`, `signals/`, `targets/` ne sont pas du scope).
- **VPS pull pattern** : sur le VPS, des modifs locales WIP sur `infrastructure/agents/platform/ingestion/specs/*.yaml` sont stashées avant chaque pull. Ne pas les écraser.

## Bugs / pièges connus

- **Endpoint `/api/datalake/dirigeant/{nom}/{prenom}`** : matching sensible aux accents ET à la casse. Trois sources interrogées en cascade : `silver.inpi_dirigeants` → `silver.dirigeants_360` → `gold.dirigeants_master`. Voir `_dirigeant_full` dans `backend/routers/datalake.py`.
- **Cards dirigeants `extractDirigeantsFromText`** dans `frontend/src/lib/dem/adapter.ts` : parser regex sur le streamedText du LLM pour matcher les noms cités. Couvre formats parens, em-dash, virgule, markdown bold (`**Nom**`), tables markdown (`| Nom | XX ans |`).
- **`ChatPanel` timeout 90s** : le LLM peut prendre plus, abort frontend → fallback `fetchPersons`. Bumper le timeout si besoin (`ChatPanel.tsx:316`).

## Production

- Domain : `https://82-165-57-191.sslip.io` (sslip.io = wildcard DNS pour TLS auto)
- SSH : `ssh -i ~/.ssh/demoema_ionos_ed25519 root@82.165.57.191`
- Containers : `demomea-{caddy,backend,frontend,agents-platform,datalake-db}` — tous via `docker compose`.
- Self-hosted Supabase **plus déployé** — utiliser variables d'env `.env` (instance externe).
