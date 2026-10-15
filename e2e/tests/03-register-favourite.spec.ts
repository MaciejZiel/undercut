import { expect, test } from "@playwright/test";
import { waitForVerificationPath } from "../helpers/mail";
import { newCredentials } from "../helpers/users";

test("register through the form, confirm the e-mail from the log, follow a driver", async ({ page, request }) => {
  const who = newCredentials("reg");

  await page.goto("/register");
  await page.getByLabel("E-mail").fill(who.email);
  await page.getByLabel("Display name").fill(who.displayName);
  await page.getByLabel("Password").fill(who.password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Check your inbox" })).toBeVisible();

  // The confirmation link is printed by the backend (console mail backend in debug mode).
  const linkPath = await waitForVerificationPath(who.email);
  await page.goto(linkPath);
  await page.getByRole("button", { name: "Confirm e-mail" }).click();
  await expect(page.getByText("Your e-mail address is confirmed.")).toBeVisible();

  // Pick the driver through the search API so the test does not depend on a slug spelling.
  const search = await request.get("/api/v1/search/?q=verstappen");
  const drivers = ((await search.json()) as { drivers: { slug: string; name: string }[] }).drivers;
  const max = drivers.find((d) => d.name.includes("Max"));
  expect(max, "Max Verstappen is in the catalog").toBeTruthy();

  await page.goto(`/drivers/${max!.slug}`);
  await page.getByRole("button", { name: /^Follow / }).click();
  await expect(page.getByRole("button", { name: /^Unfollow / })).toBeVisible();

  await expect
    .poll(async () => {
      const res = await page.request.get("/api/v1/favorites/");
      const body = (await res.json()) as { drivers: { slug: string }[] };
      return body.drivers.map((d) => d.slug);
    })
    .toContain(max!.slug);

  await page.reload();
  await expect(page.getByRole("button", { name: /^Unfollow / })).toBeVisible();
});
