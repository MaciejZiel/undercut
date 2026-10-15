import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { components } from "@/lib/api/client";
import { renderWithProviders } from "@/test/render";
import { compareHref, isReady, parseSeason, parseSlug } from "./compare-url";
import { CompareView, formatDelta, leader } from "./compare-view";

const replace = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace, push: vi.fn() }) }));

type Compare = components["schemas"]["Compare"];

const side = (slug: string, stats: Partial<Compare["a"]["stats"]> = {}): Compare["a"] => ({
  driver: { slug, name: `Driver ${slug}`, code: null, number: null },
  stats: { starts: 100, wins: 10, podiums: 30, poles: 5, fastest_laps: 3, points: 1234.5, titles: null, ...stats },
});

const compare = (over: Partial<Compare["head_to_head"]> = {}): Compare => ({
  season: null,
  a: side("alpha", { wins: 20 }),
  b: side("beta", { wins: null }),
  head_to_head: {
    races_together: 40,
    same_team_races: 20,
    race: { a_ahead: 25, b_ahead: 10, both_finished: 35 },
    qualifying: { a_ahead: 18, b_ahead: 22, compared: 40 },
    teammate_seasons: [
      { year: 2023, team_slug: "t", races: 20, lap_times: null, lap_times_reason: "Lap-time analytics are not available." },
      {
        year: 2024,
        team_slug: "t",
        races: 2,
        lap_times: [{ round: 1, name: "Bahrain GP", a_median_lap_ms: 93500, b_median_lap_ms: null, delta_ms: -120 }],
        lap_times_reason: null,
      },
    ],
    ...over,
  },
});

let fetchMock: ReturnType<typeof vi.fn>;
function stub(handler: (url: URL) => Response | Promise<Response>) {
  fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(input instanceof Request ? input.url : String(input), "http://localhost");
    if (url.pathname === "/api/v1/auth/me/") return Response.json({ is_authenticated: false, user: null });
    return handler(url);
  });
  vi.stubGlobal("fetch", fetchMock);
}
const compareCalls = () => fetchMock.mock.calls.filter(([i]) => String(i instanceof Request ? i.url : i).includes("/compare/"));

beforeEach(() => replace.mockReset());
afterEach(() => vi.unstubAllGlobals());

describe("compare url helpers", () => {
  it("parses slugs and seasons defensively", () => {
    expect(parseSlug("max-verstappen")).toBe("max-verstappen");
    expect(parseSlug("a b")).toBeNull();
    expect(parseSlug(undefined)).toBeNull();
    expect(parseSeason("2024")).toBe(2024);
    expect(parseSeason("1800")).toBeNull();
    expect(parseSeason("abc")).toBeNull();
  });
  it("builds hrefs and checks readiness", () => {
    expect(compareHref({ a: "x", b: null, season: null })).toBe("/compare?a=x");
    expect(compareHref({ a: "x", b: "y", season: 2024 })).toBe("/compare?a=x&b=y&season=2024");
    expect(isReady({ a: "x", b: "x", season: null })).toBe(false);
    expect(isReady({ a: "x", b: "y", season: null })).toBe(true);
  });
  it("finds the leader and formats deltas null-safely", () => {
    expect(leader(2, 1)).toBe("a");
    expect(leader(1, 2)).toBe("b");
    expect(leader(1, 1)).toBeNull();
    expect(leader(null, 1)).toBeNull();
    expect(formatDelta(-120)).toBe("-0.120 s");
    expect(formatDelta(1500)).toBe("+1.500 s");
    expect(formatDelta(null)).toBeNull();
  });
});

describe("CompareView", () => {
  it("asks for two drivers and does not call the API", async () => {
    stub(() => Response.json({}));
    renderWithProviders(<CompareView initial={{ a: "alpha", b: null, season: null }} />);
    expect(screen.getByText("Pick two drivers")).toBeInTheDocument();
    expect(compareCalls()).toHaveLength(0);
  });

  it("refuses the same driver twice", () => {
    stub(() => Response.json({}));
    renderWithProviders(<CompareView initial={{ a: "alpha", b: "alpha", season: null }} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Pick two different drivers.");
    expect(compareCalls()).toHaveLength(0);
  });

  it("renders stats, head to head and the reason instead of missing lap times", async () => {
    stub(() => Response.json(compare()));
    renderWithProviders(<CompareView initial={{ a: "alpha", b: "beta", season: 2024 }} />);
    const table = await screen.findByRole("table", { name: /Career statistics of Driver alpha and Driver beta/ });
    const wins = within(table).getByRole("row", { name: /Wins/ });
    expect(within(wins).getByText("20")).toBeInTheDocument();
    expect(within(wins).getByText("No data")).toBeInTheDocument(); // null never becomes 0
    expect(screen.getByText("Lap-time analytics are not available.")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: /Median race lap times/ })).toBeInTheDocument();
    expect(screen.getByText("-0.120 s")).toBeInTheDocument();
    expect(screen.getByText(/Driver alpha ahead 25 times, Driver beta ahead 10 times/)).toBeInTheDocument();
    const req = compareCalls()[0][0] as Request;
    expect(new URL(req.url).search).toBe("?a=alpha&b=beta&season=2024");
  });

  it("explains when the drivers never raced each other and hides the lap section", async () => {
    stub(() => Response.json(compare({ races_together: 0, teammate_seasons: [] })));
    renderWithProviders(<CompareView initial={{ a: "alpha", b: "beta", season: null }} />);
    expect(await screen.findByText("Never raced each other")).toBeInTheDocument();
    expect(screen.queryByText(/Team mates/)).not.toBeInTheDocument();
  });

  it("shows a not-found state for a 404 and a retry for a server error", async () => {
    stub(() => Response.json({ detail: "x" }, { status: 404 }));
    renderWithProviders(<CompareView initial={{ a: "alpha", b: "beta", season: null }} />);
    expect(await screen.findByText("Driver not found")).toBeInTheDocument();
  });

  it("shows an error with a retry for a server failure", async () => {
    stub(() => new Response("{}", { status: 500 }));
    renderWithProviders(<CompareView initial={{ a: "alpha", b: "beta", season: null }} />);
    expect(await screen.findByRole("button", { name: "Try again" }, { timeout: 4000 })).toBeInTheDocument();
  });

  it("validates the season field and writes it to the URL", () => {
    stub(() => Response.json({}));
    renderWithProviders(<CompareView initial={{ a: null, b: null, season: null }} />);
    const input = screen.getByLabelText("Season (optional)");
    fireEvent.change(input, { target: { value: "1900" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));
    expect(screen.getByRole("alert")).toHaveTextContent(/between 1950 and 2100/);
    expect(replace).not.toHaveBeenCalled();
    fireEvent.change(input, { target: { value: "2021" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));
    expect(replace).toHaveBeenCalledWith("/compare?season=2021", { scroll: false });
  });
});

describe("DriverPicker inside CompareView", () => {
  it("searches drivers and selects one with the keyboard", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      stub((url) =>
        Response.json({
          drivers: [
            { slug: "alpha", name: "Anna Alpha", code: null, number: null, nationality: null },
            { slug: "beta", name: "Ben Beta", code: null, number: null, nationality: null },
          ],
          constructors: [],
          circuits: [],
          rounds: [],
          q: url.searchParams.get("q"),
        }),
      );
      renderWithProviders(<CompareView initial={{ a: null, b: null, season: null }} />);
      const input = screen.getByRole("combobox", { name: "First driver" });
      fireEvent.focus(input);
      expect(await screen.findByText("Type at least 2 letters to search.")).toBeInTheDocument();
      fireEvent.change(input, { target: { value: "be" } });
      await act(async () => {
        await vi.advanceTimersByTimeAsync(400);
      });
      const options = await screen.findAllByRole("option");
      expect(options).toHaveLength(2);
      expect(input).toHaveAttribute("aria-activedescendant", options[0].id);
      fireEvent.keyDown(input, { key: "ArrowDown" });
      fireEvent.keyDown(input, { key: "Enter" });
      await waitFor(() => expect(replace).toHaveBeenCalledWith("/compare?a=beta", { scroll: false }));
    } finally {
      vi.useRealTimers();
    }
  });
});
