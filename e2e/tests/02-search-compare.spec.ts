import { expect, test } from "@playwright/test";

test("search to driver to compare: head to head with Hamilton", async ({ page }) => {
  await page.goto("/");

  const search = page.getByRole("combobox", { name: /Search drivers, teams, circuits and races/ });
  await search.fill("verstappen");
  await page.getByRole("option", { name: /Max Verstappen/ }).click();

  await expect(page).toHaveURL(/\/drivers\/[a-z0-9_-]+/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Verstappen");
  await expect(page.getByText("Career points").first()).toBeVisible();
  await expect(page.getByText("Pole positions").first()).toBeVisible();

  await page.getByRole("link", { name: /Compare with/ }).click();
  await expect(page).toHaveURL(/\/compare\?.*a=/);

  const second = page.getByRole("combobox", { name: "Second driver" });
  await second.click();
  await second.fill("hamilton");
  await page.getByRole("option", { name: /Lewis Hamilton/ }).click();

  await expect(page).toHaveURL(/b=/);
  await expect(page.getByRole("heading", { name: "Head to head" })).toBeVisible();
  await expect(page.getByText("Never raced each other")).toHaveCount(0);
});
