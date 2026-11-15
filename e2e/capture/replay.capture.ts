import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

const OUT = path.resolve(__dirname, "..", "capture-out");
const FRAMES = 48;
const FRAME_INTERVAL_MS = 120;

test("replay: a still and the frames of a short GIF", async ({ page }) => {
  fs.rmSync(OUT, { recursive: true, force: true });
  fs.mkdirSync(path.join(OUT, "frames"), { recursive: true });

  // Analytics are imported for 2024 round 1 only (scripts/e2e/load-data.sh).
  await page.goto("/seasons/2024/1");
  await page.getByRole("navigation", { name: "Views" }).getByRole("link", { name: "Replay" }).click();
  await expect(page).toHaveURL(/view=replay/);

  const replay = page.getByRole("region", { name: "Session replay" });
  await expect(replay).toBeVisible();
  await replay.getByLabel("Jump to lap").selectOption("20");
  await replay.getByRole("button", { name: "Speed 20x" }).click();
  await replay.scrollIntoViewIfNeeded();
  await page.evaluate(() => window.scrollBy(0, -16));

  await page.screenshot({ path: path.join(OUT, "replay.png") });

  await replay.getByRole("button", { name: "Play" }).click();
  for (let i = 0; i < FRAMES; i++) {
    await page.screenshot({ path: path.join(OUT, "frames", `${String(i).padStart(3, "0")}.png`) });
    await page.waitForTimeout(FRAME_INTERVAL_MS);
  }
  await replay.getByRole("button", { name: "Pause" }).click();
});
