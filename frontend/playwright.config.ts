import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config — qa-audit Sprint 3 (skill v3.0.0).
 *
 * Matrix : 4 navigateurs × 4 devices = 8 projets parallèles.
 * Tests E2E :
 *   - clickables-exhaustive.spec.ts (axe 1.bis : 350-400+ éléments cliquables)
 *   - browser-18cat.spec.ts         (axe 1.ter : 250 tests sur 18 catégories)
 *   - a11y.spec.ts                  (axe-core WCAG 2.2 AA)
 *
 * Run :
 *   pnpm test:e2e             — full matrix
 *   pnpm test:e2e:clickables  — uniquement axe 1.bis (chromium-desktop)
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
    // Desktop (4)
    { name: "chromium-desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox-desktop", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit-desktop", use: { ...devices["Desktop Safari"] } },
    { name: "msedge", use: { ...devices["Desktop Edge"], channel: "msedge" } },

    // Mobile + tablet (4)
    { name: "iphone-15", use: { ...devices["iPhone 15"] } },
    { name: "pixel-8", use: { ...devices["Pixel 7"] } },
    { name: "ipad", use: { ...devices["iPad Pro 11"] } },
    {
      name: "desktop-4k",
      use: { ...devices["Desktop Chrome"], viewport: { width: 3840, height: 2160 } },
    },
  ],
});
