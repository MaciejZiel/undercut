import { expect, test } from "@playwright/test";
import { confirmEmailKey, signup } from "../helpers/api";
import { keyFromPath, waitForVerificationPath } from "../helpers/mail";
import { newCredentials } from "../helpers/users";

test("register through the form, confirm the e-mail from the log, follow a driver", async ({ page, request }) => {
  const who = newCredentials("reg");

  await page.goto("/register");
  await page.getByLabel("E-mail").fill(who.email);
  await page.getByLabel("Display name").fill(who.displayName);
  await page.getByLabel("Password").fill(who.password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Check your inbox" })).toBeVisible();

  // The confirmation link is printed by the backend (console mail backend in debug mode). The
  // confirmation page cannot be used here, see the known-issue test below, so the key from the link
  // is submitted to the same endpoint the page would call.
  const linkPath = await waitForVerificationPath(who.email);
  await expect(page.getByTestId("unverified-banner")).toBeVisible();
  await confirmEmailKey(page.request, keyFromPath(linkPath));
  await page.reload();
  await expect(page.getByRole("button", { name: /^Account menu for / })).toBeVisible();
  await expect(page.getByTestId("unverified-banner")).toHaveCount(0);

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

// Known issue, found by this suite: the confirmation page sends the key from the URL to the API as
// Next.js hands it over, percent-encoded ("MQ%3A1x..." instead of "MQ:1x..."), so the API answers
// 400 and the page says "This link is invalid or has expired" for every real link. The alias page
// /account/verify-email/<key> that the mail points to also encodes the key a second time.
// `test.fail` keeps the run green while the bug exists and turns red once it is fixed, which is the
// cue to drop the annotation and to confirm through the page in the journey test above.
test("the link exactly as mailed opens the confirmation page", async ({ page, request }) => {
  test.fail(true, "the confirmation page sends the percent-encoded key to the API");
  const who = newCredentials("lnk");
  await signup(request, who);
  const linkPath = await waitForVerificationPath(who.email);

  await page.goto(linkPath);
  await expect(page.getByRole("button", { name: "Confirm e-mail" })).toBeVisible();
});
