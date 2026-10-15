import { expect, test } from "@playwright/test";
import { signup } from "../helpers/api";
import { createVerifiedUser } from "../helpers/users";

test("settings: export the data, delete the account, then register the same e-mail again", async ({
  page,
  context,
}) => {
  const who = await createVerifiedUser(context.request, "del");

  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Your data" })).toBeVisible();

  const downloading = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download my data" }).click();
  const download = await downloading;
  expect(download.suggestedFilename()).toBe("undercut-export.json");
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream) chunks.push(Buffer.from(chunk));
  const exported = JSON.parse(Buffer.concat(chunks).toString("utf8")) as unknown;
  expect(JSON.stringify(exported)).toContain(who.email);

  await page.getByRole("button", { name: "Delete my account" }).click();
  const dialog = page.getByRole("dialog", { name: "Delete your account?" });
  const confirm = dialog.getByRole("button", { name: "Delete forever" });
  await expect(confirm).toBeDisabled();
  await dialog.getByLabel(`Type "${who.displayName}" to confirm`).fill(who.displayName);
  await confirm.click();

  // Signed out: the header offers "sign in" again and the session no longer works.
  await expect(page.getByRole("link", { name: "Account: sign in" })).toBeVisible();
  const me = (await (await page.request.get("/api/v1/auth/me/")).json()) as { is_authenticated: boolean };
  expect(me.is_authenticated).toBe(false);

  // The address is free again.
  const again = context.request;
  await signup(again, who);
  await page.goto("/");
  await expect(page.getByRole("button", { name: /^Account menu for / })).toBeVisible();
});
