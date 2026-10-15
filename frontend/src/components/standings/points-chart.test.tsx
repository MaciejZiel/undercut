import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Progress } from "@/lib/api/queries";
import { PointsChart } from "./points-chart";

vi.mock("@/components/charts/echart", () => ({
  EChart: ({ label }: { label: string }) => <div data-testid="chart" aria-label={label} />,
}));

const data: Progress = {
  season: 2024,
  rounds: [1, 2],
  series: Array.from({ length: 7 }, (_, i) => ({
    entity: { id: i, slug: `d${i}`, name: `Driver ${i}`, code: `D${i}`, nationality: null },
    points: [25, 40],
    positions: [1, 1],
  })),
};

function renderChart() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <PointsChart kind="drivers" season={2024} />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("PointsChart", () => {
  it("shows five lines, toggles more, and switches to a table", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(data), { status: 200, headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    renderChart();
    await screen.findByTestId("chart");
    expect(screen.getByText("Lines (5 of 7)")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /^D6/ }));
    expect(screen.getByText("Lines (6 of 7)")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show as table" }));
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.queryByTestId("chart")).not.toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(7);
    fireEvent.click(screen.getByRole("button", { name: "Show as chart" }));
    expect(screen.getByTestId("chart")).toBeInTheDocument();
  });

  it("shows a retryable error state when the request fails", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 500, headers: { "content-type": "application/json" } })));
    renderChart();
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("shows an empty state when there is no progression", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ season: 2024, rounds: [], series: [] }), { status: 200, headers: { "content-type": "application/json" } })));
    renderChart();
    expect(await screen.findByText("No progression yet")).toBeInTheDocument();
  });
});
