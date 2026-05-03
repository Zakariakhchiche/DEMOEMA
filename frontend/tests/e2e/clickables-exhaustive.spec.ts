/**
 * Tests exhaustifs cliquables — qa-audit Sprint 3 axe 1.bis.
 *
 * Cible : 350-400+ éléments interactifs sur les 8 sections nav.
 * Couvre TOUS les cliquables (pas juste <button>) :
 * - <button>, <a href>
 * - [role=button|tab|menuitem|switch|checkbox|radio|option|link|treeitem]
 * - <input type=checkbox|radio|submit|button|reset|image>
 * - <select>, <summary>, <details>
 * - [onclick] sur n'importe quel tag
 * - [tabindex] focusables
 * - <label for>
 *
 * Run :
 *   pnpm test:e2e:clickables  (chromium-desktop)
 *   pnpm test:e2e:matrix      (8 projets cross-browser × cross-device)
 */
import { test, expect, type Page, type Locator } from "@playwright/test";

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

async function auditRoute(page: Page, route: string) {
  await page.goto(route);
  await page.waitForLoadState("networkidle");

  const elements = await page.locator(CLICKABLE_SELECTOR).all();
  const failures: Failure[] = [];
  const passes: string[] = [];

  for (const el of elements) {
    const id = await elementId(el);
    const ok = await checkOneElement(page, el, route, id, failures);
    if (ok) passes.push(id);
  }

  return { total: elements.length, failures, passes };
}

async function elementId(el: Locator): Promise<string> {
  const tag = await el.evaluate((e: Element) => e.tagName.toLowerCase());
  const role = (await el.getAttribute("role")) ?? "";
  const text = ((await el.textContent()) ?? "").trim().slice(0, 50);
  const aria = (await el.getAttribute("aria-label")) ?? "";
  return `[${tag}${role ? ` role=${role}` : ""}] "${text || aria || "(no name)"}"`;
}

async function checkOneElement(
  page: Page,
  el: Locator,
  route: string,
  id: string,
  failures: Failure[],
): Promise<boolean> {
  // 1. Accessible name
  const accessibleName = await el.evaluate((e: Element) => {
    const ariaLabel = e.getAttribute("aria-label");
    const ariaLabelledBy = e.getAttribute("aria-labelledby");
    const title = e.getAttribute("title");
    const txt = (e.textContent ?? "").trim();
    return ariaLabel || ariaLabelledBy || txt || title || "";
  });
  if (!accessibleName) {
    failures.push({ selector: id, reason: "accessibleName vide" });
    return false;
  }

  // 2. Touch target ≥ 24×24px (WCAG 2.2 AA), 20×20 toléré pour inputs
  const tag = await el.evaluate((e: Element) => e.tagName.toLowerCase());
  const box = await el.boundingBox();
  const minSize = tag === "input" ? 20 : 24;
  if (box && (box.width < minSize || box.height < minSize)) {
    failures.push({
      selector: id,
      reason: `target ${Math.round(box.width)}×${Math.round(box.height)} < ${minSize}×${minSize}`,
    });
  }

  // 3. Disabled justifié → skip click
  if (await el.isDisabled()) return true;

  // 4. Snapshot avant
  const urlBefore = page.url();
  const sigBefore = await page.evaluate(() => document.body.innerText.length);
  let networkFired = false;
  const reqHandler = () => {
    networkFired = true;
  };
  page.on("request", reqHandler);

  // 5. Action selon type
  const type = (await el.getAttribute("type")) ?? "";
  const role = (await el.getAttribute("role")) ?? "";
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
    return false;
  }
  page.off("request", reqHandler);

  // 6. Effet vérifiable
  const urlAfter = page.url();
  const sigAfter = await page.evaluate(() => document.body.innerText.length);
  const navigated = urlBefore !== urlAfter;
  const domChanged = Math.abs(sigBefore - sigAfter) > 5;
  const ariaChanged = await el.evaluate((e: Element) => {
    return Boolean(
      e.getAttribute("aria-expanded") ||
        e.getAttribute("aria-checked") ||
        e.getAttribute("aria-selected") ||
        e.getAttribute("aria-pressed"),
    );
  });

  if (!navigated && !domChanged && !networkFired && !ariaChanged) {
    failures.push({
      selector: id,
      reason: "aucun effet (no nav/DOM/network/aria)",
    });
    return false;
  }

  // Reset après nav
  if (navigated) {
    await page.goto(route);
    await page.waitForLoadState("networkidle");
  }
  return true;
}

for (const route of ROUTES) {
  test(`clickables exhaustifs ${route}`, async ({ page }) => {
    const { total, failures, passes } = await auditRoute(page, route);
    console.log(
      JSON.stringify({
        route,
        total,
        pass: passes.length,
        fail: failures.length,
        coverage_pct: total > 0 ? Math.round((passes.length / total) * 100) : 0,
      }),
    );
    expect(
      failures,
      `\n${failures.map((f) => `  - ${f.selector} → ${f.reason}`).join("\n")}\n`,
    ).toEqual([]);
  });
}
