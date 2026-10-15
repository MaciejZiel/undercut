import { beforeEach, describe, expect, it, vi } from "vitest";

const connection = vi.fn(async () => undefined);
vi.mock("next/server", () => ({ connection }));

const getDrivers = vi.fn();
const getConstructors = vi.fn();
const getCircuits = vi.fn();
const getSeasons = vi.fn();
const getSeason = vi.fn();
vi.mock("@/lib/api/queries", () => ({ getDrivers, getConstructors, getCircuits, getSeasons, getSeason }));

const page = <T,>(results: T[]) => ({ results, next: null });

beforeEach(() => {
  vi.clearAllMocks();
  getDrivers.mockResolvedValue(page([{ slug: "max-verstappen" }]));
  getConstructors.mockResolvedValue(page([{ slug: "ferrari" }]));
  getCircuits.mockResolvedValue(page([{ slug: "monza" }]));
  getSeasons.mockResolvedValue(page([{ year: 2024 }]));
  getSeason.mockResolvedValue({
    year: 2024,
    rounds: [
      { round: 1, is_cancelled: false },
      { round: 2, is_cancelled: true },
      { round: null, is_cancelled: false },
    ],
  });
});

const urls = async () => (await (await import("./sitemap")).default()).map((entry) => entry.url);

describe("sitemap", () => {
  it("renders per request, so it is not frozen at build time when the API is down", async () => {
    await urls();
    expect(connection).toHaveBeenCalledOnce();
  });

  it("lists the static routes and the catalog pages, skipping cancelled and unnumbered rounds", async () => {
    const all = await urls();
    expect(all.some((u) => u.endsWith("/about"))).toBe(true);
    expect(all.some((u) => u.endsWith("/drivers/max-verstappen"))).toBe(true);
    expect(all.some((u) => u.endsWith("/constructors/ferrari"))).toBe(true);
    expect(all.some((u) => u.endsWith("/circuits/monza"))).toBe(true);
    expect(all.some((u) => u.endsWith("/seasons/2024"))).toBe(true);
    expect(all.filter((u) => /\/seasons\/2024\/\d+$/.test(u))).toHaveLength(1);
  });

  it("falls back to the static routes when the API fails", async () => {
    getDrivers.mockRejectedValue(new Error("API unreachable"));
    const all = await urls();
    expect(all.length).toBeGreaterThan(0);
    expect(all.some((u) => u.includes("/drivers/"))).toBe(false);
  });
});
