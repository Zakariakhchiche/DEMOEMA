# Contributing to DEMOEMA

## Overview

DEMOEMA is proprietary software. External contributions are not accepted. This document is for the core team and contracted developers.

## Workflow

1. **Branch from `develop`**. Name: `chore/<topic>`, `feat/<topic>`, `fix/<topic>`.
2. **One PR = one coherent lot**. Reference the audit brief lot (L0, L1, …) or the Jira ticket (SCRUM-XX) in the PR description.
3. **Commits** follow Conventional Commits: `type(scope): message`. Types: `feat`, `fix`, `refactor`, `chore`, `test`, `docs`, `ci`.
4. **Tests** must be green (backend `pytest`, frontend `npm run test`) before opening PR.
5. **Lint** must pass (`ruff check`, `ruff format --check`, `mypy backend/`, `npm run lint`).
6. **CI must be green** before merge. No `--no-verify`, no skip CI.
7. **Review required** — at least one approval (Zak until the team grows).
8. **Squash merge** by default to keep `develop` linear.

## Local setup

```bash
# Backend
cd backend
pip install -r requirements.txt
pip install -e ".[dev]"   # installs ruff, mypy, pytest

# Frontend
cd frontend
npm install

# Pre-commit hooks
pip install pre-commit
pre-commit install

# Full stack via Docker
docker compose up -d
curl http://localhost:8000/docs
curl http://localhost:3000
```

## Secrets

Do not commit `.env`, `.env.signups`, `secrets/`, credentials, SSH keys, tokens. Secrets live encrypted in `secrets/*.sops.yaml` (via SOPS + age — see `docs/SECRETS_OPERATIONS.md`).

Gitleaks runs on every PR and before every commit via pre-commit hook.

## Testing

- Unit tests: fast, no IO. Located in `backend/tests/unit/` and `frontend/src/__tests__/`.
- Integration tests: require Docker test stack. `@pytest.mark.integration` in backend, separate Vitest config `vitest.integration.config.ts` in frontend.
- E2E tests: Playwright under `frontend/e2e/`. Run with `npm run e2e`.

## Deploying

**Never deploy manually.** Merging to `develop` triggers `.github/workflows/deploy-ionos.yml`. If the CI fails, investigate and fix — do not bypass.

Rollback: `infrastructure/scripts/rollback.sh <sha>`. Each deploy is logged in `docs/DEPLOY_LOG.md`.

## Questions

Questions, clarifications, or blockers: `davyly1@gmail.com`.

## License

By contributing to this repository, you agree that your contributions will be licensed under the same proprietary license as the project (see `LICENSE`).
