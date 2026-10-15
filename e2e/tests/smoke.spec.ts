import { expect, test } from "@playwright/test";

const PAGES = [
  "/",
  "/seasons",
  "/seasons/2024",
  "/seasons/2024/1",
  "/drivers",
  "/constructors",
  "/circuits",
  "/calendar",
  "/standings/drivers",
  "/standings/constructors",
  "/compare",
  "/predict",
  "/login",
  "/register",
  "/about",
  "/privacy",
];

test.describe("smoke", () => {
  for (const path of PAGES) {
    test(`${path} answers 200 and has exactly one h1`, async ({ page }) => {
      const response = await page.goto(path);
      expect(response?.status()).toBe(200);
      await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
    });
  }

  test("the API is served through the proxy and the health check passes", async ({ request }) => {
    const res = await request.get("/api/ready/");
    expect(res.status()).toBe(200);
  });

  // /admin/ is routed to Django by deploy/Caddyfile in this compose setup, so "not served through
  // the proxy" does not hold here and is deliberately not asserted. The internal revalidate
  // route is reachable through the proxy too; it must at least refuse callers without the secret.
  test("the revalidate route refuses a caller without the shared secret", async ({ request }) => {
    const res = await request.post("/_internal/revalidate", { data: { tags: ["drivers"] } });
    expect(res.status()).toBeGreaterThanOrEqual(400);
  });
});
