import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config — DEMOEMA QA L4 (cf. docs/QA_PLAYBOOKS.md §5 axe 1)
 *
 * Cible : matrix 4 navigateurs × 4 devices = 8 projets pour cross-browser/cross-device
 * Tests :
 *   - clickables-exhaustive.spec.ts : 350-400+ éléments cliquables (1.bis)
 *   - browser-18cat.spec.ts         : 250 tests sur 18 catégories (1.ter)
 *   - a11y.spec.ts                  : axe-core WCAG 2.2 AA
 *   - visual.spec.ts                : régression visuelle Playwright snapshots
 *
 * Run :
 *   pnpm test:e2e             — full matrix
 *   pnpm test:e2e:clickables  — uniquement axe 1.bis (chromium-desktop)
 *   pnpm test:e2e:browser     — uniquement axe 1.ter (chromium-desktop)
 *   pnpm test:e2e:matrix      — cross-browser × cross-device
 */
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI
    ? [["github"], ["html", { open: "never" }]]
    : [["list"], ["html", { open: "never" }]],

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3010",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    locale: "fr-FR",
    timezoneId: "Europe/Paris",
    colorScheme: "light",
  },

  projects: [
    // Desktop browsers (4 projets)
    { name: "chromium-desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox-desktop", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit-desktop", use: { ...devices["Desktop Safari"] } },
    { name: "msedge", use: { ...devices["Desktop Edge"], channel: "msedge" } },

    // Mobile devices (4 projets)
    { name: "iphone-15", use: { ...devices["iPhone 15"] } },
    { name: "pixel-8", use: { ...devices["Pixel 7"] } },
    { name: "ipad", use: { ...devices["iPad Pro 11"] } },
    {
      name: "desktop-4k",
      use: { ...devices["Desktop Chrome"], viewport: { width: 3840, height: 2160 } },
    },
  ],

  webServer: process.env.CI
    ? undefined
    : {
        command: "pnpm dev",
        url: "http://localhost:3010",
        reuseExistingServer: true,
        timeout: 120_000,
      },
});
