import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { components } from "@/lib/api/client";
import { PositionChange, QualifyingResultsTable, RaceResultsTable } from "./results-tables";

type Race = components["schemas"]["RaceResult"];
type Quali = components["schemas"]["QualifyingResult"];

const team = { slug: "red_bull", name: "Red Bull", color: "#3671c6" };
const race = (over: Partial<Race> & { slug: string }): Race => ({
  position: 1,
  position_text: "1",
  driver: { slug: over.slug, name: `Driver ${over.slug}`, code: null, number: null },
  team,
  grid: 2,
  laps: 57,
  status: "Finished",
  time_ms: 5527123,
  best_lap_ms: 90000,
  points: 25,
  fastest_lap: false,
  position_change: 1,
  ...over,
});

describe("RaceResultsTable", () => {
  it("renders winner time, gap, status, points and linked names", () => {
    render(
      <RaceResultsTable
        caption="2024 Test GP race results"
        results={[
          race({ slug: "a" }),
          race({ slug: "b", position: 2, position_text: "2", time_ms: 5527123 + 5234, points: 18, position_change: 0, fastest_lap: true }),
        ]}
      />,
    );
    expect(screen.getByRole("table", { name: "2024 Test GP race results" })).toBeInTheDocument();
    const rows = screen.getAllByRole("row");
    const winner = within(rows[1]);
    expect(winner.getByRole("link", { name: "Driver a" })).toHaveAttribute("href", "/drivers/a");
    expect(winner.getByRole("link", { name: "Red Bull" })).toHaveAttribute("href", "/constructors/red_bull");
    expect(winner.getByText("1:32:07.123")).toBeInTheDocument();
    expect(winner.getByText("25")).toBeInTheDocument();
    const second = within(rows[2]);
    expect(second.getByText("+5.234")).toBeInTheDocument();
    expect(second.getByTitle("Fastest lap")).toBeInTheDocument();
  });

  it("shows laps down for a lapped car instead of a time", () => {
    render(
      <RaceResultsTable
        caption="2024 Test GP race results"
        results={[
          race({ slug: "a" }),
          race({ slug: "z", position: 15, position_text: "15", laps: 56, status: "Lapped", time_ms: 5530000, points: 0 }),
        ]}
      />,
    );
    expect(within(screen.getAllByRole("row")[2]).getByText("+1 lap")).toBeInTheDocument();
  });

  it("shows em dashes for nulls and the retirement code, never zeros", () => {
    render(
      <RaceResultsTable
        caption="r"
        results={[
          race({
            slug: "dnf",
            position: null,
            position_text: "R",
            time_ms: null,
            laps: null,
            grid: null,
            points: null,
            status: null,
            position_change: null,
            fastest_lap: null,
          }),
        ]}
      />,
    );
    const row = within(screen.getAllByRole("row")[1]);
    expect(row.getByText("R")).toBeInTheDocument();
    expect(row.getAllByTitle(/No data|No grid position/).length).toBeGreaterThanOrEqual(4);
    expect(row.queryByText("0")).toBeNull();
    expect(row.queryByTitle("Fastest lap")).toBeNull();
  });

  it("labels a pit lane start instead of showing grid 0", () => {
    render(<RaceResultsTable caption="r" results={[race({ slug: "p", grid: 0, position_change: null })]} />);
    expect(screen.getByText("Pit lane")).toBeInTheDocument();
  });
});

describe("PositionChange", () => {
  it("shows an up arrow with text for places gained", () => {
    render(<PositionChange change={3} />);
    expect(screen.getByTitle("Gained 3 places")).toHaveTextContent("▲");
    expect(screen.getByText("Gained 3 places")).toHaveClass("sr-only");
  });

  it("shows a down arrow for places lost and a dash for no data", () => {
    const { rerender } = render(<PositionChange change={-2} />);
    expect(screen.getByTitle("Lost 2 places")).toHaveTextContent("▼");
    rerender(<PositionChange change={null} />);
    expect(screen.getByTitle("No grid position")).toHaveTextContent("—");
  });
});

const q = (slug: string, over: Partial<Quali> = {}): Quali => ({
  position: 1,
  driver: { slug, name: `Driver ${slug}`, code: null, number: null },
  team,
  q1_ms: 90123,
  q2_ms: 89456,
  q3_ms: 88999,
  eliminated_in: null,
  ...over,
});

describe("QualifyingResultsTable", () => {
  it("shows Q1 to Q3 and highlights eliminated drivers", () => {
    render(
      <QualifyingResultsTable
        caption="Qualifying"
        results={[q("a"), q("b", { position: 16, q2_ms: null, q3_ms: null, eliminated_in: "Q1" })]}
      />,
    );
    expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Pos", "Driver", "Team", "Q1", "Q2", "Q3"]);
    expect(screen.getByText("1:28.999")).toBeInTheDocument();
    expect(screen.getByText("out in Q1")).toBeInTheDocument();
    expect(screen.getAllByTitle("No data")).toHaveLength(2);
  });

  it("uses a single time column for old formats", () => {
    render(<QualifyingResultsTable caption="Qualifying" results={[q("a", { q2_ms: null, q3_ms: null })]} />);
    expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Pos", "Driver", "Team", "Time"]);
  });
});
