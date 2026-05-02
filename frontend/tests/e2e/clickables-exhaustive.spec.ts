/**
 * Tests exhaustifs des éléments cliquables — DEMOEMA QA L4 axe 1.bis
 * Cible : 350-400+ éléments interactifs sur 14 routes, 100 % testés
 *
 * Couvre TOUS les cliquables (pas juste <button>) :
 * - <button>, <a href>
 * - [role=button|tab|menuitem|switch|checkbox|radio|option|treeitem|link]
 * - <input type=checkbox|radio|submit|button|reset|image>
 * - <select>, <summary>
 * - [onclick] sur n'importe quel tag
 * - [tabindex] focusables
 * - <label for>
 *
 * Cf. docs/QA_PLAYBOOKS.md §5 Sous-axe 1.bis pour les 10 critères.
 */
import { test, expect, type Page } from "@playwright/test";

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

const CLICKABLE_SELECTOR = [
  "button:visible",
  "a[href]:visible",
  '[role="button"]:visible',
  '[role="link"]:visible',
  '[role="menuitem"]:visible',
  '[role="tab"]:visible',
  '[role="switch"]:visible',
  '[role="checkbox"]:visible',
  '[role="radio"]:visible',
  '[role="option"]:visible',
  '[role="treeitem"]:visible',
  'input[type="checkbox"]:visible',
  'input[type="radio"]:visible',
  'input[type="submit"]:visible',
  'input[type="button"]:visible',
  'input[type="reset"]:visible',
  'input[type="image"]:visible',
  "select:visible",
  "summary:visible",
  "[onclick]:visible",
  '[tabindex]:not([tabindex="-1"]):visible',
  "label[for]:visible",
].join(", ");

type Failure = { selector: string; reason: string };

async function auditClickablesOnRoute(page: Page, route: string): Promise<{
  total: number;
  failures: Failure[];
  passes: string[];
}> {
  await page.goto(route);
  await page.waitForLoadState("networkidle");

  const elements = await page.locator(CLICKABLE_SELECTOR).all();
  const failures: Failure[] = [];
  const passes: string[] = [];

  for (const el of elements) {
    const tag = await el.evaluate((e: Element) => e.tagName.toLowerCase());
    const role = (await el.getAttribute("role")) ?? "";
    const type = (await el.getAttribute("type")) ?? "";
    const text = ((await el.textContent()) ?? "").trim().slice(0, 60);
    const aria = (await el.getAttribute("aria-label")) ?? "";
    const id = `[${tag}${role ? ` role=${role}` : ""}${type ? ` type=${type}` : ""}] "${text || aria}"`;
    const box = await el.boundingBox();

    // 1. Accessible name
    const accessibleName = (await el.evaluate((e: Element) => {
      const ariaLabel = e.getAttribute("aria-label");
      const ariaLabelledBy = e.getAttribute("aria-labelledby");
      const title = e.getAttribute("title");
      const txt = (e.textContent ?? "").trim();
      return ariaLabel || ariaLabelledBy || txt || title || "";
    })) as string;

    if (!accessibleName) {
      failures.push({ selector: id, reason: "accessibleName vide" });
      continue;
    }

    // 2. Touch target ≥ 24×24 (WCAG 2.2 AA), 20×20 toléré pour inputs natifs
    const minSize = tag === "input" ? 20 : 24;
    if (box && (box.width < minSize || box.height < minSize)) {
      failures.push({
        selector: id,
        reason: `target ${Math.round(box.width)}×${Math.round(box.height)} < ${minSize}×${minSize}`,
      });
    }

    // 3. Disabled justifié OK
    if (await el.isDisabled()) {
      passes.push(`${id} [disabled-OK]`);
      continue;
    }

    // 4. Snapshot avant action
    const urlBefore = page.url();
    const sigBefore = await page.evaluate(() => document.body.innerText.length);
    let networkFired = false;
    const reqHandler = () => {
      networkFired = true;
    };
    page.on("request", reqHandler);

    // 5. Action selon type
    try {
      if (
        type === "checkbox" ||
        type === "radio" ||
        role === "checkbox" ||
        role === "switch"
      ) {
        await el.check({ timeout: 2000 });
      } else if (tag === "select") {
        const opts = await el.locator("option").all();
        if (opts.length > 1) await el.selectOption({ index: 1 });
      } else {
        await el.click({ timeout: 2000 });
      }
      await page.waitForTimeout(300);
    } catch (e) {
      page.off("request", reqHandler);
      failures.push({
        selector: id,
        reason: `interaction failed: ${(e as Error).message.slice(0, 80)}`,
      });
      continue;
    }
    page.off("request", reqHandler);

    // 6. Assertion d'effet (nav / DOM mutation / network / aria-state)
    const urlAfter = page.url();
    const sigAfter = await page.evaluate(() => document.body.innerText.length);
    const navigated = urlBefore !== urlAfter;
    const domChanged = Math.abs(sigBefore - sigAfter) > 5;
    const ariaChanged = await el.evaluate((e: Element) => {
      const expanded = e.getAttribute("aria-expanded");
      const checked = e.getAttribute("aria-checked");
      const selected = e.getAttribute("aria-selected");
      const pressed = e.getAttribute("aria-pressed");
      return Boolean(expanded || checked || selected || pressed);
    });

    if (!navigated && !domChanged && !networkFired && !ariaChanged) {
      failures.push({
        selector: id,
        reason: "aucun effet (no nav/DOM/network/aria)",
      });
    } else {
      passes.push(id);
    }

    // Reset après nav
    if (navigated) {
      await page.goto(route);
      await page.waitForLoadState("networkidle");
    }
  }

  return { total: elements.length, failures, passes };
}

for (const route of ROUTES) {
  test(`clickables exhaustifs sur ${route}`, async ({ page }) => {
    const { total, failures, passes } = await auditClickablesOnRoute(page, route);

    console.log(
      JSON.stringify({
        route,
        total,
        pass: passes.length,
        fail: failures.length,
        coverage_pct: total > 0 ? (passes.length / total) * 100 : 0,
      }),
    );

    expect(
      failures,
      `\n${failures.map((f) => `  - ${f.selector} → ${f.reason}`).join("\n")}\n`,
    ).toEqual([]);
  });
}
