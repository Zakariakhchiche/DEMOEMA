/**
 * E2E — Accessibility scan @axe-core/playwright — qa-audit Sprint 6.
 *
 * Boucle 8 routes nav, run injectAxe + checkA11y, assert 0 violations
 * level "serious" ou "critical". Output JSON par route dans test-results/.
 *
 * Pré-requis :
 *   pnpm add -D @axe-core/playwright
 *
 * Run :
 *   pnpm test:e2e tests/e2e/a11y.spec.ts
 *
 * Note Sprint 6 : NE TOURNE PAS localement (browsers Playwright pas installés).
 */
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { writeFileSync, mkdirSync, existsSync } from "node:fs";
import path from "node:path";

const ROUTES = [
  "/#dashboard",
  "/#chat",
  "/#explorer",
  "/#pipeline",
  "/#audit",
  "/#graph",
  "/#compare",
  "/#signals",
];

const REPORT_DIR = path.join("test-results", "a11y");
if (!existsSync(REPORT_DIR)) {
  mkdirSync(REPORT_DIR, { recursive: true });
}

for (const route of ROUTES) {
  test(`a11y scan: ${route}`, async ({ page }) => {
    await page.goto(route);
    await expect(page.locator("body")).toBeVisible();

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    // Output JSON par route
    const safeName = route.replace(/[^a-z0-9]/gi, "_");
    writeFileSync(
      path.join(REPORT_DIR, `${safeName}.json`),
      JSON.stringify(accessibilityScanResults, null, 2),
    );

    // Filtrer violations critiques/sérieuses
    const criticalViolations = accessibilityScanResults.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );

    expect(
      criticalViolations,
      `Violations critiques/sérieuses sur ${route}:\n` +
        criticalViolations
          .map((v) => `  - [${v.impact}] ${v.id}: ${v.help}`)
          .join("\n"),
    ).toEqual([]);
  });
}
