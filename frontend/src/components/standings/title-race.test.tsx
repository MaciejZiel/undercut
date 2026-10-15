import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { components } from "@/lib/api/client";

const getTitleRace = vi.fn();
vi.mock("./title-race-data", () => ({ getTitleRace: (s?: number) => getTitleRace(s) }));
vi.mock("next/server", () => ({ connection: async () => {} }));

import { TitleRacePanel, TitleRaceSection } from "./title-race";

type Race = components["schemas"]["TitleRace"];
const ent = (id: number, slug: string) => ({ id, slug, name: `Driver ${slug}`, code: null, nationality: null });

const open: Race = {
  season: 2025,
  after_round: 20,
  rounds_remaining: 4,
  sprints_remaining: 1,
  max_points_available: 108,
  fastest_lap_point: false,
  decided: false,
  champion: null,
  decided_in_round: null,
  message: null,
  eliminated: 17,
  contenders: [
    { position: 1, entity: ent(1, "a"), points: 300, max_points: 408, gap_to_leader: 0, tie_break_needed: false },
    { position: 2, entity: ent(2, "b"), points: 200, max_points: 308, gap_to_leader: 100, tie_break_needed: true },
  ],
};

describe("TitleRacePanel", () => {
  it("lists contenders with current and maximum points and the chance", () => {
    render(<TitleRacePanel race={open} />);
    expect(screen.getByText(/4 rounds and 1 sprint left, at most 108 points/)).toBeInTheDocument();
    expect(screen.getByText(/17 drivers can no longer win/)).toBeInTheDocument();
    const rows = screen.getAllByRole("row");
    expect(within(rows[1]).getByText("408")).toBeInTheDocument();
    expect(within(rows[1]).queryByText("Possible")).toBeNull();
    expect(within(rows[2]).getByText("Only on countback")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Leader, or level with the leader")).toBeInTheDocument();
  });

  it("announces a decided championship", () => {
    render(
      <TitleRacePanel
        race={{ ...open, decided: true, champion: ent(1, "a"), decided_in_round: 21, message: "Champion decided in round 21", contenders: [open.contenders[0]] }}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Driver a is the champion. Champion decided in round 21.");
    expect(screen.getByText("Champion")).toBeInTheDocument();
  });

  it("renders nothing without a season and a note without contenders", () => {
    const { container } = render(<TitleRacePanel race={{ ...open, season: null }} />);
    expect(container).toBeEmptyDOMElement();
    render(<TitleRacePanel race={{ ...open, contenders: [], rounds_remaining: null }} />);
    expect(screen.getByText("No driver is left in the title race.")).toBeInTheDocument();
    expect(screen.getByText(/Remaining rounds are not known/)).toBeInTheDocument();
  });
});

describe("TitleRaceSection", () => {
  const thisYear = new Date().getUTCFullYear();
  it("skips past seasons and rounds, queries the current one", async () => {
    getTitleRace.mockResolvedValue(open);
    expect(await TitleRaceSection({ searchParams: Promise.resolve({ season: "1999" }) })).toBeNull();
    expect(await TitleRaceSection({ searchParams: Promise.resolve({ after_round: "3" }) })).toBeNull();
    expect(getTitleRace).not.toHaveBeenCalled();
    const el = await TitleRaceSection({ searchParams: Promise.resolve({ season: String(thisYear) }) });
    expect(el).not.toBeNull();
    expect(getTitleRace).toHaveBeenCalledWith(thisYear);
  });
  it("shows a local error when the API fails", async () => {
    getTitleRace.mockRejectedValue(new Error("down"));
    const el = await TitleRaceSection({ searchParams: Promise.resolve({}) });
    render(el);
    expect(screen.getByRole("alert")).toHaveTextContent("Could not load the title race");
  });
});
