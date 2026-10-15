import { afterEach, describe, expect, it, vi } from "vitest";
import { mockFetch } from "@/test/fetch-mock";
import { fetchPickableDrivers, findNextRound, formatCountdown, parseInviteCode, remainingMs, serverSkew, upcomingRounds } from "./api";

const round = (n: number, extra: Record<string, unknown> = {}) => ({ round: n, name: `GP ${n}`, date: "2026-01-01", is_cancelled: false, has_sprint: false, circuit: {}, winner: null, ...extra });
const state = (n: number, status: string) => ({ state: { round: { id: n, year: 2026, round: n, name: `GP ${n}` }, status, closes_at: "2026-03-01T10:00:00Z", my_pick: null } });

afterEach(() => vi.unstubAllGlobals());

describe("countdown maths", () => {
  it("uses the server skew, never goes negative", () => {
    const closes = "2026-03-01T10:00:00Z";
    const t = Date.parse(closes);
    expect(remainingMs(closes, 0, t - 5000)).toBe(5000);
    // browser clock 10 s behind the server: the server says it is already t, so 0 left
    expect(remainingMs(closes, 10_000, t - 10_000)).toBe(0);
    expect(remainingMs(closes, 0, t + 99_999)).toBe(0);
    expect(remainingMs(null, 0)).toBeNull();
  });
  it("formats days and clock", () => {
    expect(formatCountdown(((2 * 24 + 3) * 3600 + 4 * 60 + 5) * 1000)).toBe("2d 03:04:05");
    expect(formatCountdown(59_000)).toBe("00:00:59");
  });
  it("reads the Date header of a response", () => {
    const r = new Response("{}", { headers: { Date: "Sat, 01 Mar 2026 10:00:00 GMT" } });
    expect(Math.abs(serverSkew(r) - (Date.parse("2026-03-01T10:00:00Z") - Date.now()))).toBeLessThan(1000);
    expect(serverSkew(new Response("{}"))).toBe(0);
  });
});

describe("round selection", () => {
  it("keeps upcoming, non-cancelled rounds in order", () => {
    const rounds = [round(1, { winner: { slug: "a" } }), round(3), round(2, { is_cancelled: true }), round(4)] as never;
    expect(upcomingRounds(rounds)).toEqual([3, 4]);
  });

  it("returns the first round the server reports as open", async () => {
    mockFetch({
      "GET /api/v1/seasons/": { body: { results: [{ year: 2025 }, { year: 2026 }] } },
      "GET /api/v1/seasons/2026/": { body: { rounds: [round(1, { winner: {} }), round(2), round(3)] } },
      "GET /api/v1/predictions/rounds/2026/2/": { body: state(2, "closed").state },
      "GET /api/v1/predictions/rounds/2026/3/": { body: state(3, "open").state },
    });
    const next = await findNextRound();
    expect(next).toMatchObject({ kind: "round", year: 2026 });
    expect(next.kind === "round" && next.result.state.round.round).toBe(3);
  });

  it("falls back to the first closed round, and to none when the season is over", async () => {
    mockFetch({
      "GET /api/v1/seasons/": { body: { results: [{ year: 2026 }] } },
      "GET /api/v1/seasons/2026/": { body: { rounds: [round(2)] } },
      "GET /api/v1/predictions/rounds/2026/2/": { body: state(2, "closed").state },
    });
    expect((await findNextRound()).kind).toBe("round");
    mockFetch({
      "GET /api/v1/seasons/": { body: { results: [{ year: 2026 }] } },
      "GET /api/v1/seasons/2026/": { body: { rounds: [round(1, { winner: {} })] } },
    });
    expect((await findNextRound()).kind).toBe("none");
  });
});

describe("drivers and invite codes", () => {
  it("keeps only drivers that carry a numeric id", async () => {
    mockFetch({
      "GET /api/v1/drivers/": { body: { results: [{ id: 5, given_name: "Max", family_name: "Verstappen", code: "VER", number: 1 }, { given_name: "No", family_name: "Id", code: null, number: null }] } },
    });
    expect(await fetchPickableDrivers(2026)).toEqual([{ id: 5, name: "Max Verstappen", code: "VER", number: 1 }]);
  });
  it("accepts a code or an invite link", () => {
    expect(parseInviteCode(" ab12cd ")).toBe("AB12CD");
    expect(parseInviteCode("https://undercut.example/leagues/join/ab12cd?x=1")).toBe("AB12CD");
  });
});
