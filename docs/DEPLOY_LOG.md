# DEMOEMA — Deploy Log

Journal de tous les déploiements prod. Une ligne par deploy, du plus récent au plus ancien.

Format : `YYYY-MM-DD HH:MM UTC | deployer | prev_sha → new_sha | component | notes`.

Le script `infrastructure/scripts/deploy.sh` append une entry automatiquement. En cas de deploy manuel (exceptionnel), l'ajouter ici à la main avant `docker compose up -d`.

Le rollback (`rollback.sh <sha>`) s'appuie sur ce log pour identifier le commit de retour arrière sûr. **Ne supprimez jamais une ligne de ce log** — marquer `[ROLLED BACK]` plutôt.

---

## 2026-04

_(à remplir au premier deploy post-fix CI)_

<!-- Exemple de format:
2026-04-24 09:15 UTC | github-actions (sha=abc1234) | d4e5f6a → abc1234 | all | first deploy after L0 hot fixes
2026-04-24 14:30 UTC | zak-manual | abc1234 → def5678 | backend | hotfix CORS incident (SENTRY-14523) — [ROLLED BACK 2026-04-24 15:05]
2026-04-24 15:05 UTC | zak-manual (rollback) | def5678 → abc1234 | all | rollback after 500 spike
-->
