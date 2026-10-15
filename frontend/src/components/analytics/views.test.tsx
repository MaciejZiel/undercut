import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/components/charts/echart", () => ({
  EChart: ({ label }: { label: string }) => <div role="img" aria-label={label} />,
}));
vi.mock("./setup", () => ({}));

import { AnalyticsPanel } from "./analytics-panel";

const header = { year: 2024, round: 1, round_name: "Test GP", type: "RACE", status: "results_final" };
const drv = (code: string, id: number) => ({
  driver_id: id, code, full_name: code, constructor_id: id, constructor_name: "Team" + id, color_hex: null,
});
const bodies: Record<string, unknown> = {
  positions: {
    session: header, laps: [1, 2],
    drivers: [{ ...drv("VER", 1), positions: [1, 1], pit_laps: [2] }, { ...drv("NOR", 2), positions: [2, 2], pit_laps: [] }],
    neutralisations: [],
  },
  stints: {
    session: header,
    drivers: [{ ...drv("VER", 1), position: 1, stints: [{ stint_number: 1, compound: "SOFT", compound_letter: "S", lap_start: 1, lap_end: 2, laps: 2, tyre_age_at_start: 0 }] }],
  },
  "pit-stops": {
    session: header, method: "lane_duration",
    stops: [{ driver_id: 1, driver_code: "VER", constructor_id: 1, constructor_name: "Team1", color_hex: null, lap: 2, stop_ms: 2400, lane_ms: 21000, compound_from: "SOFT", compound_to: "HARD" }],
    ranking: [{ rank: 1, constructor_id: 1, constructor_name: "Team1", color_hex: null, driver_code: "VER", lap: 2, duration_ms: 21000 }],
  },
  laps: {
    session: header, hide_slow: true, neutralisations: [],
    drivers: [{ ...drv("VER", 1), lap_numbers: [1, 2], duration_ms: [90000, 89000], sector1_ms: [30000, 29500], sector2_ms: [30000, null], sector3_ms: [30000, 30000], summary: { count: 2, best_ms: 89000, median_ms: 89500, stdev_ms: 707, } }],
  },
};

const calls: string[] = [];
beforeEach(() => {
  calls.length = 0;
  vi.stubGlobal("fetch", vi.fn(async (input: Request | string) => {
    const url = typeof input === "string" ? input : input.url;
    calls.push(url);
    if (url.includes("/analytics/weather/")) {
      return new Response(JSON.stringify({ detail: "nope", analytics_available: false }), { status: 404, headers: { "content-type": "application/json" } });
    }
    const kind = /analytics\/([a-z-]+)\//.exec(url)?.[1] ?? "";
    return new Response(JSON.stringify(bodies[kind]), { status: 200, headers: { "content-type": "application/json" } });
  }));
});
afterEach(() => vi.unstubAllGlobals());

function renderPanel(view: "analysis" | "strategy") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <AnalyticsPanel view={view} year={2024} round={1} session="RACE" />
    </QueryClientProvider>,
  );
}

describe("analytics views", () => {
  it("shows a loading state then the position chart with legend, source and table toggle", async () => {
    renderPanel("analysis");
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(await screen.findByRole("img", { name: /position by lap/ })).toBeInTheDocument();
    expect(screen.getByText("Data: OpenF1")).toBeInTheDocument();
    expect(screen.getByText(/Rotate your phone to see more/)).toBeInTheDocument();
    const ver = screen.getByRole("button", { name: /VER/ });
    fireEvent.click(ver);
    expect(ver).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Show as table" }));
    expect(screen.getByRole("table")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Full screen" }));
    expect(screen.getByRole("button", { name: "Exit full screen" })).toBeInTheDocument();
  });

  it("requests the top 3 laps with hide_slow on and refetches when toggled", async () => {
    renderPanel("analysis");
    fireEvent.click(screen.getByRole("button", { name: "Lap times" }));
    await screen.findByRole("img", { name: /lap times/ });
    const first = calls.find((u) => u.includes("/analytics/laps/")) ?? "";
    expect(first).toContain("drivers=VER%2CNOR");
    expect(first).toContain("hide_slow=true");
    expect(screen.getByText("1:29.000")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Hide in/out and safety-car laps"));
    await waitFor(() => expect(calls.some((u) => u.includes("hide_slow=false"))).toBe(true));
  });

  it("names the pit stop ranking method", async () => {
    renderPanel("analysis");
    fireEvent.click(screen.getByRole("button", { name: "Pit stops" }));
    expect(await screen.findByText(/Ranked by pit lane duration/)).toBeInTheDocument();
    expect(screen.getByText("S → H")).toBeInTheDocument();
  });

  it("renders stint bars with compound letters", async () => {
    renderPanel("strategy");
    expect(await screen.findByRole("list", { name: /Tyre stints/ })).toBeInTheDocument();
    expect(screen.getByText("Soft tyre, 2 laps")).toBeInTheDocument();
  });

  it("shows an empty state when the API reports no analytics", async () => {
    renderPanel("analysis");
    fireEvent.click(screen.getByRole("button", { name: "Weather" }));
    expect(await screen.findByText("No detailed analytics for this season")).toBeInTheDocument();
  });
});
