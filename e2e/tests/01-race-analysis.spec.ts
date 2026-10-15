import { expect, test } from "@playwright/test";
import { trackCspViolations } from "../helpers/csp";

test("dashboard to race analysis: positions chart renders and has a table alternative", async ({ page }) => {
  const violations = trackCspViolations(page);
  await page.goto("/");
  const lastRace = page.getByRole("link", { name: /Full results and analysis/ });
  await expect(lastRace).toBeVisible();
  await lastRace.click();
  await expect(page).toHaveURL(/\/seasons\/\d{4}\/\d+/);

  // Analytics were imported for one race only (2024 round 1), so the rest of the test uses it.
  await page.goto("/seasons/2024/1");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("2024");

  await page.getByRole("navigation", { name: "Views" }).getByRole("link", { name: "Analysis" }).click();
  await expect(page).toHaveURL(/view=analysis/);

  const chart = page.getByRole("img", { name: /position by lap/i });
  await expect(chart).toBeVisible();
  await expect(chart.locator("canvas").first()).toBeVisible();
  await expect
    .poll(async () => {
      const box = await chart.boundingBox();
      return box ? Math.min(box.width, box.height) : 0;
    })
    .toBeGreaterThan(50);

  await page.getByRole("button", { name: "Show as table" }).click();
  await expect(page.getByRole("table", { name: /Position of every driver/ })).toBeVisible();
  await expect(chart).toHaveCount(0);

  await page.getByRole("button", { name: "Show as chart" }).click();
  await expect(page.getByRole("img", { name: /position by lap/i })).toBeVisible();
  expect(violations, violations.join("\n")).toEqual([]);
});
