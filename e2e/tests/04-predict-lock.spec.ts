import { expect, test } from "@playwright/test";
import { apiSend } from "../helpers/api";
import { seedRound } from "../helpers/compose";
import { createVerifiedUser } from "../helpers/users";

type Slot = { id: number };
type RoundState = {
  status: "open" | "closed" | "unavailable";
  closes_at: string | null;
  my_pick: { p1: Slot; p2: Slot; p3: Slot; pole: Slot; fastest_lap: Slot } | null;
};

const SLOTS: { label: string; index: number }[] = [
  { label: "Winner (P1)", index: 0 },
  { label: "Second place (P2)", index: 1 },
  { label: "Third place (P3)", index: 2 },
  { label: "Pole position", index: 3 },
  { label: "Fastest lap", index: 4 },
];

test("predict: a full pick is saved while open and refused after the lock", async ({ page, context }) => {
  const { year, round } = await seedRound();
  const roundApi = `/api/v1/predictions/rounds/${year}/${round}/`;
  await createVerifiedUser(context.request, "pred");

  await page.goto(`/predict/${year}/${round}`);
  await expect(page.getByText("Predictions close in")).toBeVisible();

  for (const slot of SLOTS) {
    await page.getByRole("combobox", { name: slot.label }).click();
    await page.getByRole("listbox", { name: slot.label }).getByRole("option").nth(slot.index).click();
  }
  await page.getByRole("button", { name: "Save pick" }).click();
  await expect(page.getByText(/Pick saved/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Update pick" })).toBeVisible();

  const open = (await (await context.request.get(roundApi)).json()) as RoundState;
  expect(open.status).toBe("open");
  expect(open.my_pick, "the pick is stored").not.toBeNull();
  const pick = open.my_pick!;
  const payload = {
    p1: pick.p1.id,
    p2: pick.p2.id,
    p3: pick.p3.id,
    pole: pick.pole.id,
    fastest_lap: pick.fastest_lap.id,
  };

  // Qualifying "starts": the server closes the round, whatever the browser still shows.
  const locked = await seedRound({ lock: true });
  expect(locked.locked).toBe(true);

  const refused = await apiSend(context.request, "PUT", roundApi, payload);
  expect(refused.status()).toBe(403);
  expect(((await refused.json()) as { code: string }).code).toBe("predictions_locked");

  const after = (await (await context.request.get(roundApi)).json()) as RoundState;
  expect(after.status).toBe("closed");
  expect(after.my_pick?.p1.id, "the saved pick is untouched").toBe(pick.p1.id);

  await page.reload();
  await expect(page.getByText(/Predictions for this round are closed/)).toBeVisible();
  await expect(page.getByRole("button", { name: /Save pick|Update pick/ })).toHaveCount(0);
  await expect(page.getByRole("combobox", { name: "Winner (P1)" })).toHaveCount(0);
});
