import { defineConfig, devices } from "@playwright/test";
import { BASE_URL, contextOptions } from "./helpers/config";

/**
 * Captures the README media (replay GIF frames and screenshots) from the Compose stack in CI.
 * Kept apart from the test suite: `npx playwright test --config capture.config.ts`.
 */
export default defineConfig({
  testDir: "./capture",
  testMatch: "**/*.capture.ts",
  outputDir: "./capture-results",
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 20_000 },
  reporter: [["list"]],
  use: {
    ...contextOptions,
    baseURL: BASE_URL,
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 860 }, colorScheme: "dark" },
    },
  ],
});
