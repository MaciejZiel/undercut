import { expect, request as requestFactory, test } from "@playwright/test";
import { BASE_URL, contextOptions } from "../helpers/config";
import { createVerifiedUser, loginThroughForm } from "../helpers/users";

test("leagues: create, share the invite code, a second user joins and both are listed", async ({
  page,
  context,
  browser,
}) => {
  const owner = await createVerifiedUser(context.request, "own");
  const leagueName = `E2E league ${Date.now()}`;

  await page.goto("/leagues");
  await page.getByLabel("League name").fill(leagueName);
  await page.getByRole("button", { name: "Create league" }).click();

  await expect(page).toHaveURL(/\/leagues\/[A-Z0-9]{8}$/);
  await expect(page.getByRole("heading", { name: leagueName })).toBeVisible();
  const inviteCode = (await page.locator("code").first().innerText()).trim();
  expect(inviteCode).toMatch(/^[A-Z0-9]{8}$/);

  // A second person, in a browser context of their own (separate cookies and session).
  const signup = await requestFactory.newContext({ baseURL: BASE_URL, ...contextOptions });
  const guest = await createVerifiedUser(signup, "gst");
  await signup.dispose();

  const guestContext = await browser.newContext({ baseURL: BASE_URL, ...contextOptions });
  try {
    const guestPage = await guestContext.newPage();
    await loginThroughForm(guestPage, guest);

    await guestPage.goto("/leagues");
    await guestPage.getByLabel("Invite code or link").fill(inviteCode);
    await guestPage.getByRole("button", { name: "Join league" }).click();

    await expect(guestPage).toHaveURL(new RegExp(`/leagues/${inviteCode}$`));
    const guestMembers = guestPage.getByRole("region", { name: "Members" });
    await expect(guestMembers).toContainText(owner.displayName);
    await expect(guestMembers).toContainText(guest.displayName);
  } finally {
    await guestContext.close();
  }

  await page.reload();
  const members = page.getByRole("region", { name: "Members" });
  await expect(members).toContainText(owner.displayName);
  await expect(members).toContainText(guest.displayName);
  await expect(page.getByText("2 of")).toBeVisible();
});
