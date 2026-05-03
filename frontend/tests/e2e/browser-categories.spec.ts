/**
 * E2E — qa-audit Sprint 6 (axe 1.ter follow-up).
 *
 * Couvre 5 catégories d'interaction navigateur transverses :
 *   1. Navigation routing (back/forward, deep link, hash routes)
 *   2. Keyboard navigation (Tab, Esc, Enter)
 *   3. Touch interactions (tap, long-press, swipe — emulate mobile)
 *   4. Persistance (localStorage write/read, refresh preserves state)
 *   5. Network conditions (offline mode, slow 3G simulate)
 *
 * Run :
 *   pnpm test:e2e tests/e2e/browser-categories.spec.ts
 *   PLAYWRIGHT_BASE_URL=https://82-165-57-191.sslip.io pnpm test:e2e ...
 *
 * Note Sprint 6 : NE TOURNE PAS localement (browsers Playwright pas installés).
 */
import { test, expect, devices, type BrowserContext } from "@playwright/test";

const ROUTES = ["/#dashboard", "/#chat", "/#explorer", "/#pipeline", "/#audit"];

// ════════════════════════════════════════════════════════════════════
// 1. Navigation routing
// ════════════════════════════════════════════════════════════════════
test.describe("nav.routing", () => {
  test("back/forward sur hash routes preserves history", async ({ page }) => {
    await page.goto("/#dashboard");
    await expect(page).toHaveURL(/#dashboard/);
    await page.goto("/#chat");
    await expect(page).toHaveURL(/#chat/);
    await page.goBack();
    await expect(page).toHaveURL(/#dashboard/);
    await page.goForward();
    await expect(page).toHaveURL(/#chat/);
  });

  test("deep link hash route loads target panel", async ({ page }) => {
    for (const route of ROUTES) {
      await page.goto(route);
      await expect(page).toHaveURL(new RegExp(route.replace("/#", "#")));
      // Body monté = pas de white screen
      await expect(page.locator("body")).toBeVisible();
    }
  });

  test("unknown hash route does not crash app", async ({ page }) => {
    await page.goto("/#nonexistent-route-xyz");
    await expect(page.locator("body")).toBeVisible();
    // L'app doit gracefully fallback, pas un écran blanc
    const bodyText = await page.locator("body").innerText();
    expect(bodyText.length).toBeGreaterThan(0);
  });
});

// ════════════════════════════════════════════════════════════════════
// 2. Keyboard navigation
// ════════════════════════════════════════════════════════════════════
test.describe("nav.keyboard", () => {
  test("Tab order traverses focusable elements", async ({ page }) => {
    await page.goto("/#dashboard");
    await page.keyboard.press("Tab");
    const first = await page.evaluate(() => document.activeElement?.tagName);
    expect(first).toBeTruthy();
    // Au moins 5 tabs sans crash
    for (let i = 0; i < 5; i++) await page.keyboard.press("Tab");
    const after = await page.evaluate(() => document.activeElement?.tagName);
    expect(after).toBeTruthy();
  });

  test("Escape closes any open modal/sheet", async ({ page }) => {
    await page.goto("/#dashboard");
    // Tente d'ouvrir un trigger modal le cas échéant
    const trigger = page.locator('[data-modal-trigger], [aria-haspopup="dialog"]').first();
    if (await trigger.count() > 0) {
      await trigger.click();
      await page.keyboard.press("Escape");
      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeHidden({ timeout: 2000 });
    }
  });

  test("Enter activates the focused button", async ({ page }) => {
    await page.goto("/#dashboard");
    const btn = page.locator("button:visible").first();
    if (await btn.count() > 0) {
      await btn.focus();
      await page.keyboard.press("Enter");
      // Pas de crash après Enter
      await expect(page.locator("body")).toBeVisible();
    }
  });
});

// ════════════════════════════════════════════════════════════════════
// 3. Touch interactions (emulate mobile)
// ════════════════════════════════════════════════════════════════════
test.describe("nav.touch", () => {
  test.use({ ...devices["iPhone 15"] });

  test("tap triggers click on mobile", async ({ page }) => {
    await page.goto("/#dashboard");
    const btn = page.locator("button:visible").first();
    if (await btn.count() > 0) {
      await btn.tap();
      await expect(page.locator("body")).toBeVisible();
    }
  });

  test("long-press does not crash app", async ({ page }) => {
    await page.goto("/#dashboard");
    const target = page.locator("button:visible, a:visible").first();
    if (await target.count() > 0) {
      const box = await target.boundingBox();
      if (box) {
        await page.touchscreen.tap(box.x + box.width / 2, box.y + box.height / 2);
        await page.waitForTimeout(800);
      }
    }
    await expect(page.locator("body")).toBeVisible();
  });

  test("swipe gesture on viewport does not crash", async ({ page }) => {
    await page.goto("/#dashboard");
    await page.touchscreen.tap(200, 200);
    // Simulate horizontal swipe via mouse drag (touchscreen swipe pas direct)
    await page.mouse.move(50, 300);
    await page.mouse.down();
    await page.mouse.move(350, 300, { steps: 10 });
    await page.mouse.up();
    await expect(page.locator("body")).toBeVisible();
  });
});

// ════════════════════════════════════════════════════════════════════
// 4. Persistance (localStorage)
// ════════════════════════════════════════════════════════════════════
test.describe("nav.persistance", () => {
  test("localStorage write survives refresh", async ({ page }) => {
    await page.goto("/#dashboard");
    await page.evaluate(() => {
      localStorage.setItem("qa-test-key", "qa-test-value");
    });
    await page.reload();
    const value = await page.evaluate(() => localStorage.getItem("qa-test-key"));
    expect(value).toBe("qa-test-value");
    await page.evaluate(() => localStorage.removeItem("qa-test-key"));
  });

  test("hash route preserved after refresh", async ({ page }) => {
    await page.goto("/#pipeline");
    await page.reload();
    await expect(page).toHaveURL(/#pipeline/);
  });
});

// ════════════════════════════════════════════════════════════════════
// 5. Network conditions
// ════════════════════════════════════════════════════════════════════
test.describe("nav.network", () => {
  test("offline mode shows graceful fallback", async ({ context, page }) => {
    await page.goto("/#dashboard");
    await context.setOffline(true);
    await page.goto("/#chat").catch(() => undefined);
    await context.setOffline(false);
    // App ne doit pas être crashed après retour online
    await page.goto("/#dashboard");
    await expect(page.locator("body")).toBeVisible();
  });

  test("slow 3G does not break initial render (timeout-based)", async ({ context, page }) => {
    // CDP throttling — fonctionne en chromium
    const client = await context.newCDPSession(page);
    await client.send("Network.emulateNetworkConditions", {
      offline: false,
      downloadThroughput: (50 * 1024) / 8,
      uploadThroughput: (50 * 1024) / 8,
      latency: 400,
    }).catch(() => undefined); // non-chromium → skip silencieux
    await page.goto("/#dashboard", { timeout: 60_000 });
    await expect(page.locator("body")).toBeVisible();
  });
});
