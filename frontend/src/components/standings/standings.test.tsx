import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Progress, StandingRow } from "@/lib/api/queries";
import { StandingsTable } from "./standings-table";
import { ProgressTable } from "./progress-table";
import { buildProgressOption, defaultSelection, toggleSelection } from "./progress-option";

const row = (over: Partial<StandingRow> & { slug: string }): StandingRow => ({
  position: 1,
  position_text: "1",
  entity: { id: 1, slug: over.slug, name: `Name ${over.slug}`, code: "AAA", nationality: null },
  points: 400,
  wins: 10,
  podiums: 15,
  gap_to_leader: 0,
  ...over,
});

const progress: Progress = {
  season: 2024,
  rounds: [1, 2, 3],
  series: Array.from({ length: 7 }, (_, i) => ({
    entity: { id: i, slug: `d${i}`, name: `Driver ${i}`, code: `D${i}`, nationality: null },
    points: [25, 43.5, null],
    positions: [1, 2, null],
  })),
};

type Opt = { series: { data: unknown }[]; color: string[]; yAxis: { inverse: boolean; min: number } };
const tokens = { fg: "#000", muted: "#555", line: "#ccc", surface: "#fff", accent: "#00f", palette: ["#111", "#222", "#333"] };

describe("StandingsTable", () => {
  it("renders linked drivers, points and a dash for the leader gap", () => {
    render(
      <StandingsTable
        kind="drivers"
        caption="Driver standings"
        rows={[row({ slug: "a" }), row({ slug: "b", position: 2, position_text: "2", entity: { id: 2, slug: "b", name: "Name b", code: null, nationality: null }, points: 1234.5, wins: 0, gap_to_leader: 12.5 })]}
      />,
    );
    expect(screen.getByRole("table", { name: "Driver standings" })).toBeInTheDocument();
    const rows = screen.getAllByRole("row");
    expect(within(rows[1]).getByRole("link", { name: "Name a" })).toHaveAttribute("href", "/drivers/a");
    expect(within(rows[1]).getByText("Championship leader")).toBeInTheDocument();
    expect(within(rows[2]).getByText("1,234.5")).toBeInTheDocument();
    expect(within(rows[2]).getByText("-12.5")).toBeInTheDocument();
    expect(within(rows[2]).getByText("0")).toBeInTheDocument();
  });

  it("links constructors and marks unclassified rows with a dash", () => {
    render(
      <StandingsTable
        kind="constructors"
        caption="c"
        rows={[row({ slug: "red_bull", position: null, position_text: "-" })]}
      />,
    );
    expect(screen.getByRole("link", { name: "Name red_bull" })).toHaveAttribute("href", "/constructors/red_bull");
    expect(screen.getByText("Not classified")).toBeInTheDocument();
  });
});

describe("progress helpers", () => {
  it("selects the first five by default and toggles in series order", () => {
    const sel = defaultSelection(progress);
    expect(sel).toEqual(["d0", "d1", "d2", "d3", "d4"]);
    expect(toggleSelection(progress, sel, "d6")).toEqual(["d0", "d1", "d2", "d3", "d4", "d6"]);
    expect(toggleSelection(progress, sel, "d0")).toEqual(["d1", "d2", "d3", "d4"]);
  });

  it("builds a points option and an inverted position axis", () => {
    const pts = buildProgressOption(progress, ["d1", "d2"], "points", tokens) as unknown as Opt;
    expect(pts.series).toHaveLength(2);
    expect(pts.series[0].data).toEqual([25, 43.5, null]);
    expect(pts.color).toEqual(["#222", "#333"]);
    expect(pts.yAxis.inverse).toBe(false);
    const pos = buildProgressOption(progress, ["d1"], "position", tokens) as unknown as Opt;
    expect(pos.yAxis.inverse).toBe(true);
    expect(pos.yAxis.min).toBe(1);
  });
});

describe("ProgressTable", () => {
  it("lists selected entities per round with dashes for gaps", () => {
    render(<ProgressTable data={progress} selected={["d0"]} metric="points" caption="Progress" />);
    const table = screen.getByRole("table", { name: "Progress" });
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(2);
    expect(within(rows[1]).getByText("43.5")).toBeInTheDocument();
    expect(within(rows[1]).getByText("No data")).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "R3" })).toBeInTheDocument();
  });
});
