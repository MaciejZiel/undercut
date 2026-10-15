import { defineConfig, devices } from "@playwright/test";
import { BASE_URL, contextOptions } from "./helpers/config";

const inCi = !!process.env.CI;

export default defineConfig({
  testDir: "./tests",
  workers: 1,
  fullyParallel: false,
  retries: inCi ? 1 : 0,
  forbidOnly: inCi,
  timeout: 90_000,
  expect: { timeout: 20_000 },
  reporter: inCi ? [["list"], ["html", { open: "never" }]] : [["list"]],
  use: {
    ...contextOptions,
    baseURL: BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
