import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { confirmEmailKey, signup, whoAmI, type Credentials } from "./api";
import { PASSWORD } from "./config";
import { keyFromPath, waitForVerificationPath } from "./mail";

/** Unique per run and per call: the database of the e2e stack is never reset between tests. */
export function newCredentials(prefix: string): Credentials {
  const stamp = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  return {
    email: `e2e-${prefix}-${stamp}@example.com`,
    // 3 to 20 characters and unique.
    displayName: `${prefix.slice(0, 6)}${Math.random().toString(36).slice(2, 8)}`,
    password: PASSWORD,
  };
}

/** Registers through the API, confirms the address from the e-mail in the log. Leaves the context signed in. */
export async function createVerifiedUser(request: APIRequestContext, prefix: string): Promise<Credentials> {
  const who = newCredentials(prefix);
  await signup(request, who);
  const linkPath = await waitForVerificationPath(who.email);
  await confirmEmailKey(request, keyFromPath(linkPath));
  const me = await whoAmI(request);
  expect(me?.email_verified, "the e-mail address is confirmed").toBe(true);
  return who;
}

/** Signs in through the login form. */
export async function loginThroughForm(page: Page, who: Credentials): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("E-mail").fill(who.email);
  await page.getByLabel("Password").fill(who.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("button", { name: /^Account menu for / })).toBeVisible();
}
