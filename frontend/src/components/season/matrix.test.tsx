import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { components } from "@/lib/api/client";
import { SeasonMatrix, describeCell } from "./matrix";

vi.mock("./data", () => ({ getSeasonMatrix: async () => null }));

type Matrix = components["schemas"]["Matrix"];

const team = { slug: "t", name: "Team", color: "#ff0000" };
const matrix: Matrix = {
  year: 2024,
  rounds: [
    { round: 1, name: "Bahrain Grand Prix", date: "2024-03-02", country: "Bahrain" },
    { round: 2, name: "Saudi Arabian Grand Prix", date: "2024-03-09", country: "Saudi Arabia" },
    { round: 3, name: "Australian Grand Prix", date: "2024-03-24", country: "Australia" },
  ],
  drivers: [
    {
      slug: "max",
      name: "Max V",
      code: "VER",
      position: 1,
      points: 51,
      team,
      cells: [
        { position: 1, category: "win" },
        { position: 3, category: "podium" },
        { position: null, category: "dnf" },
      ],
    },
    {
      slug: "sub",
      name: "Sub Driver",
      code: null,
      position: null,
      points: 0,
      team,
      // The API sends null for "did not take part" although the generated type omits it.
      cells: [null, { position: 9, category: "points" }, { position: 14, category: "no_points" }] as unknown as Matrix["drivers"][number]["cells"],
    },
  ],
};

describe("SeasonMatrix", () => {
  it("renders a labelled grid with a symbol and text in every category", () => {
    render(<SeasonMatrix matrix={matrix} />);
    const table = screen.getByRole("table", { name: /2024 race results by driver and round/ });
    const max = within(table).getByRole("row", { name: /Max V/ });
    expect(within(max).getByText("Max V, Bahrain Grand Prix: Win, position 1")).toBeInTheDocument();
    expect(within(max).getByText("Max V, Australian Grand Prix: Did not finish")).toBeInTheDocument();
    expect(within(max).getByText("DNF")).toBeInTheDocument();
    expect(max.textContent).toContain("★");
    expect(max.textContent).toContain("▲");
    expect(max.textContent).toContain("✕");
    const sub = within(table).getByRole("row", { name: /Sub Driver/ });
    expect(within(sub).getByText("Sub Driver, Bahrain Grand Prix: Did not take part")).toBeInTheDocument();
    expect(sub.textContent).toContain("●");
    expect(sub.textContent).toContain("○");
  });

  it("has a sticky first column and a scrolling container of its own", () => {
    render(<SeasonMatrix matrix={matrix} />);
    const row = screen.getByRole("rowheader", { name: /Max V/ });
    expect(row.className).toContain("sticky");
    expect(screen.getByRole("region", { name: /scrolls horizontally/ }).className).toContain("overflow-x-auto");
    expect(screen.getByRole("columnheader", { name: "Round 2, Saudi Arabian Grand Prix" })).toBeInTheDocument();
  });

  it("shows an empty state without data", () => {
    render(<SeasonMatrix matrix={null} />);
    expect(screen.getByText("No results yet")).toBeInTheDocument();
    render(<SeasonMatrix matrix={{ ...matrix, drivers: [] }} />);
    expect(screen.getAllByText("No results yet")).toHaveLength(2);
  });

  it("describes cells without inventing numbers", () => {
    expect(describeCell(null)).toEqual({ text: "", label: "Did not take part" });
    expect(describeCell({ position: null, category: "dnf" }).text).toBe("DNF");
  });
});
