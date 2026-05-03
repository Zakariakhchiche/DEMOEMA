# QA Testing Guide — DEMOEMA

Guide opérationnel pour l'équipe : écrire / lancer / debugger les tests
backend + frontend de DEMOEMA. Issu du Sprint QA-L4.6 (skill `qa-audit`).

## Sommaire

1. [Stack de tests](#stack)
2. [Écrire un test Hypothesis (property-based)](#hypothesis)
3. [Écrire un test pytest négatif](#negative)
4. [Écrire un test E2E Playwright](#playwright)
5. [Lancer chaque suite localement](#run)
6. [Debugger un test flaky](#flaky)
7. [Liens utiles](#links)

---

## <a name="stack"></a>1. Stack de tests

| Couche | Outil | Localisation | Markers |
|---|---|---|---|
| Unit pur | `pytest` | `backend/tests/test_*.py` | `@pytest.mark.unit` |
| Property-based | `hypothesis` | `backend/tests/properties/` | `unit` + `property` |
| Negative | `pytest` paramétré | `backend/tests/test_negative_*.py` | `negative` + `integration` |
| Integration API | `httpx.AsyncClient` | `backend/tests/test_endpoints.py` | `integration` |
| E2E browser | `playwright` | `frontend/tests/e2e/` | spec.ts |
| A11y | `@axe-core/playwright` | `frontend/tests/e2e/a11y.spec.ts` | spec.ts |

Markers déclarés dans `backend/pyproject.toml` (section `[tool.pytest.ini_options]`).

---

## <a name="hypothesis"></a>2. Écrire un test Hypothesis

### Template canonique

```python
"""Property-based tests sur <module>."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from hypothesis import given, settings, strategies as st  # type: ignore

mod = pytest.importorskip("<module_path>")  # graceful skip


@pytest.mark.unit
@pytest.mark.property
@given(siren=st.text(alphabet="0123456789", min_size=9, max_size=9))
@settings(max_examples=200, deadline=None)
def test_siren_invariant(siren: str) -> None:
    """Invariant : f(x) doit toujours satisfaire P(f(x))."""
    result = mod.process(siren)
    assert len(result) == 9
```

### Best practices

- **`max_examples=200`** par défaut, **300** pour fonctions critiques (validators).
- **`deadline=None`** pour éviter false-positives sur CI lente.
- **`pytest.importorskip`** en haut → tests sautent gracefully si le module
  est absent (utile pour code optionnel).
- Définir des **stratégies réutilisables** : `valid_siren_strategy()`,
  `invalid_siren_strategy()` (cf. `test_validators_invariants.py`).
- Tester **3 catégories** par fonction : happy paths, negative paths,
  idempotence (`f(f(x)) == f(x)`).
- Utiliser `@pytest.mark.unit + @pytest.mark.property` (les deux markers).
- Pour filtres trop restrictifs, supprimer `HealthCheck.filter_too_much`.

### Anti-patterns

- Pas de `@given` sans `@settings(deadline=None)` → flaky en CI.
- Ne pas générer de `floats(allow_nan=True)` sauf si la fonction le gère.
- Ne pas mocker dans Hypothesis → utilise du pur.

---

## <a name="negative"></a>3. Écrire un test pytest négatif

### Template

```python
INVALID_INPUTS = [
    pytest.param("", id="empty"),
    pytest.param("ABCDEFGHI", id="letters_only"),
    pytest.param("'; DROP TABLE--", id="sqli"),
]

@pytest.mark.integration
@pytest.mark.negative
@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", INVALID_INPUTS)
async def test_endpoint_rejects(app_client, invalid: str) -> None:
    """Inputs douteux → 4xx/5xx, jamais leak ni 500 inattendu."""
    resp = await app_client.get(f"/api/foo/{invalid}")
    assert resp.status_code in {400, 404, 422}
```

### Best practices

- Toujours `@pytest.mark.negative` pour faciliter `pytest -m negative`.
- Cibler les **6 grandes familles** : SIREN/SIRET malformé, dates impossibles,
  SQL injection basique, JSON malformé, headers manquants, auth expirée.
- Vérifier `status_code != 500` plutôt que valeur exacte (la cible est
  l'absence de crash, pas la spec exacte).
- Vérifier l'absence de **leak** dans le body (`pg_catalog`, `root:`, etc.).

---

## <a name="playwright"></a>4. Écrire un test E2E Playwright

### Template browser-categories

```ts
import { test, expect, devices } from "@playwright/test";

test.describe("nav.routing", () => {
  test("hash route deep link", async ({ page }) => {
    await page.goto("/#dashboard");
    await expect(page).toHaveURL(/#dashboard/);
  });
});

test.describe("nav.touch", () => {
  test.use({ ...devices["iPhone 15"] });
  test("tap triggers click", async ({ page }) => {
    await page.goto("/#dashboard");
    await page.locator("button").first().tap();
  });
});
```

### Best practices

- **8 routes nav** comme cible standard : `dashboard, chat, explorer, pipeline,
  audit, graph, compare, signals`.
- Utiliser `await expect(page.locator("body")).toBeVisible()` comme smoke check.
- Pour mobile : `test.use({ ...devices["iPhone 15"] })` au niveau describe.
- Pour réseau : `context.setOffline(true)` ou CDP `Network.emulateNetworkConditions`.

### A11y (axe-core)

```ts
import AxeBuilder from "@axe-core/playwright";
const results = await new AxeBuilder({ page })
  .withTags(["wcag2a", "wcag2aa"]).analyze();
const critical = results.violations.filter(v => v.impact === "critical");
expect(critical).toEqual([]);
```

---

## <a name="run"></a>5. Lancer chaque suite localement

```bash
# Backend — unit + property only (rapide, ~5s)
cd backend && pytest tests/properties/ -v -p no:schemathesis --no-cov

# Backend — negative endpoints
cd backend && pytest tests/test_negative_endpoints.py -v
SKIP_INTEGRATION_TESTS=1 pytest tests/test_negative_endpoints.py  # skip total

# Backend — full suite avec coverage
cd backend && pytest --cov=. --cov-report=term-missing

# Frontend — Playwright (matrice 8 projets)
cd frontend && pnpm test:e2e
cd frontend && pnpm test:e2e tests/e2e/a11y.spec.ts        # un seul spec
cd frontend && pnpm test:e2e tests/e2e/browser-categories.spec.ts

# Frontend — install browsers (une fois)
cd frontend && pnpm exec playwright install chromium
```

### Filtrage par marker

```bash
pytest -m "unit and property"        # property-based seulement
pytest -m "negative"                 # tous les tests négatifs
pytest -m "not integration"          # skip integration tests
```

---

## <a name="flaky"></a>6. Debugger un test flaky

1. **Reproduire** : `pytest path/to/test.py::test_name --count=20` (avec
   `pytest-repeat`). Si flaky, on l'attrape rapidement.
2. **Hypothesis** : ajouter `--hypothesis-show-statistics` pour voir le seed
   problématique. Reproduire avec `@reproduce_failure(seed)`.
3. **Asyncio** : si timeout aléatoire → augmenter `deadline`, vérifier les
   `asyncio.wait_for(timeout=N)` dans le code.
4. **Playwright** : `--retries=0 --workers=1` pour isoler. Examiner trace
   dans `test-results/<test>/trace.zip` (`pnpm exec playwright show-trace`).
5. **Race conditions** : recourir à `await expect(...).toHaveText(...)` plutôt
   qu'à `page.waitForTimeout(N)`.
6. **Mutation testing** : `mutmut run` (config `backend/mutmut_config.py`)
   pour voir si le test détecte effectivement les mutations.

---

## <a name="links"></a>7. Liens utiles

- [`docs/SPRINT_3_QA_AUDIT.md`](./SPRINT_3_QA_AUDIT.md) — audit initial
- [`docs/SECURITY_REVIEW_2026-04.md`](./SECURITY_REVIEW_2026-04.md) — rev sécu
- [`backend/pyproject.toml`](../backend/pyproject.toml) — markers + coverage
- [`frontend/playwright.config.ts`](../frontend/playwright.config.ts) — matrice
- Hypothesis : <https://hypothesis.readthedocs.io/>
- axe-core : <https://github.com/dequelabs/axe-core>
- Playwright : <https://playwright.dev/>

---

_Dernière mise à jour : Sprint QA-L4.6 (2026-05-01)._
