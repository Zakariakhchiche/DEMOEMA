# QA L4 — Plan d'adoption (progression)

Suivi de l'adoption du skill `qa-audit` v3.0.0 (niveau L4) sur DEMOEMA.
Cible finale : **QCS >= 90 / 100** d'ici fin juillet 2026.

> QCS = Quality Composite Score (10 dimensions, ponderation v3.0.0).
> Baseline 2026-04-30 : **20.3 / 100** (audit initial post-purge Pappers).

## Sprints livres

| Sprint   | Theme                              | Dimensions                   | PR / Commit                                       | Statut    |
|----------|------------------------------------|------------------------------|---------------------------------------------------|-----------|
| 1        | Bootstrap qa-l4 extras             | tooling, deps                | `c3b3031` feat(qa-l4): Sprint 1 bootstrap         | livre     |
| 1.5      | Hypothesis property-based scoring  | dim 3 path coverage          | `e790210` feat(qa-l4): Sprint 1.5                 | livre     |
| 1.6      | Validators + markers neg/property  | dim 3 + neg test             | `1cff058` feat(qa-l4): Sprint 1.6                 | livre     |
| 2 + 3    | Soda Core + mutmut CI + Playwright | dim 4 mutation, dim 8 data Q | `5d82fff` feat(qa-l4): Sprint 2 + 3 scaffolding   | livre     |
| 4        | DeepEval LLM tool coverage         | dim 7 LLM judge              | `feat/qa-l4-sprint1-bootstrap` (this branch)      | scaffold  |
| 5        | Bandit SAST + pip-audit + SBOM     | dim 6 sec_static, dim 9 SC   | `feat/qa-l4-sprint1-bootstrap` (this branch)      | scaffold  |

## Fichiers cles introduits Sprint 4 + 5

- `backend/tests/eval/test_copilot_quality.py` — 10 cas baseline + 4 metriques DeepEval
- `backend/tests/test_sast_config_valid.py` — validation offline config Bandit
- `backend/.bandit` + section `[tool.bandit]` dans `backend/pyproject.toml`
- `.github/workflows/qa-security.yml` — CI hebdo bandit + pip-audit + SBOM CycloneDX

## QCS estime par sprint

| Apres sprint | QCS estime | Delta | Justification                                                  |
|--------------|------------|-------|----------------------------------------------------------------|
| Baseline     | 20.3       |   -   | Audit initial 2026-04-30                                       |
| 1 + 1.5 + 1.6| 28        | +7.7  | Hypothesis + Schemathesis + branch coverage                    |
| 2 + 3        | 38        | +10   | Soda 8 tables + mutmut CI + Playwright UI                      |
| 4 + 5        | ~50       | +12   | DeepEval scaffold + Bandit SARIF + pip-audit + SBOM hebdo      |
| 6 (cible)    | ~70       | +20   | TLA+ light + A/B shadow + dashboard 15D + threshold-based gate |
| Final        | >= 90      | +20   | Mutation 80%, branch 70%, all dims green                       |

## Sprints restants

### Sprint 6 — modeles formels + observabilite QA (~3 semaines)

- **TLA+ light** — specifier le state-machine du copilot SSE (start, stream, abort, fallback fetchPersons). Cible : 1 spec `.tla` runnable via TLC, 0 deadlock detecte. Module : `backend/specs/copilot_sse.tla`.
- **A/B shadow eval** — router 5 % du trafic prod copilot vers une route shadow `/api/copilot/stream?shadow=1`, comparer reponses cote a cote sur 7 jours (DeepSeek vs candidat). Stocker dans `qa_shadow_runs` (enrichir, ne pas creer table).
- **Dashboard QA 15 dimensions** — page Next.js `/admin/qa-dashboard` (auth admin) qui agrege artifacts de tous les workflows (mutmut score, soda checks, bandit findings, deepeval scores). Source unique de verite QCS live.
- **Threshold-based PR gate** — bloquer merge si QCS regresse > 5 pts vs main.

## Liens

- Skill source : `~/.claude/skills/qa-audit/SKILL.md`
- Preset projet : `~/.claude/skills/qa-audit/presets/demoema.yaml`
- Branche en cours : `feat/qa-l4-sprint1-bootstrap`
- Issue tracker : SCRUM-160 (epic QA L4 adoption)

## Notes operationnelles

- DeepEval : NE PAS installer dans le venv local (judge OpenAI = paye). Ne run que sur CI runner avec secret `OPENAI_API_KEY` ou `LOCAL_LLM_JUDGE_URL` (DeepSeek vLLM).
- Bandit : la config est dans 2 fichiers (`backend/.bandit` + `[tool.bandit]`) — `test_sast_config_valid.py` enforce leur synchronisation.
- mutmut : Linux-only (issue mutmut #397 sur Windows). CI-only, pas de run local sur la machine de dev Zak.
