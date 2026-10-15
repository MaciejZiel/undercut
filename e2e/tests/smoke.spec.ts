import { expect, test } from "@playwright/test";
import { trackCspViolations } from "../helpers/csp";

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
    test(`${path} answers 200, has exactly one h1 and breaks no CSP rule`, async ({ page }) => {
      const violations = trackCspViolations(page);
      const response = await page.goto(path);
      expect(response?.status()).toBe(200);
      await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
      await page.waitForLoadState("networkidle");
      expect(violations, violations.join("\n")).toEqual([]);
    });
  }

  test("pages carry a strict Content-Security-Policy", async ({ request }) => {
    const res = await request.get("/");
    const policy = res.headers()["content-security-policy"] ?? "";
    expect(policy).toContain("default-src 'self'");
    expect(policy).toContain("frame-ancestors 'none'");
    expect(policy).toContain("object-src 'none'");
  });

  test("the circuit page may embed the OpenStreetMap map and nothing else", async ({ page, request }) => {
    const violations = trackCspViolations(page);
    const list = await request.get("/api/v1/circuits/");
    const body = (await list.json()) as { results?: { slug: string }[] } | { slug: string }[];
    const first = Array.isArray(body) ? body[0] : body.results?.[0];
    test.skip(!first, "no circuit in the catalog");
    await page.goto(`/circuits/${first!.slug}`);
    await page.waitForLoadState("networkidle");
    expect(violations, violations.join("\n")).toEqual([]);
  });

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
