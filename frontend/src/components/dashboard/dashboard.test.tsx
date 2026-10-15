import { act, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { components } from "@/lib/api/client";
import type { Standings } from "@/lib/api/queries";
import { Countdown } from "./countdown";
import { countdownParts, pickRaces } from "./pick-races";
import { PodiumCards } from "./podium-cards";
import { TopFive } from "./top-five";

type Round = components["schemas"]["CalendarRound"];
const winner = { driver: { slug: "a", name: "A", code: null, number: null }, team: { slug: "t", name: "T", color: null } };
const rd = (n: number, date: string, over: Partial<Round> = {}): Round => ({
  round: n,
  name: `GP ${n}`,
  date,
  is_cancelled: false,
  has_sprint: false,
  circuit: { slug: "c", name: "C", country: null } as Round["circuit"],
  winner: null,
  ...over,
});

describe("pickRaces", () => {
  it("finds the next upcoming and the last completed round, skipping cancelled", () => {
    const rounds = [
      rd(1, "2024-03-01", { winner }),
      rd(2, "2024-03-15", { winner }),
      rd(3, "2024-04-01", { is_cancelled: true }),
      rd(4, "2024-04-15"),
      rd(5, "2024-05-01"),
    ];
    const { next, last } = pickRaces(rounds, "2024-04-02");
    expect(next?.round).toBe(4);
    expect(last?.round).toBe(2);
  });
  it("returns nulls for an empty or finished season", () => {
    expect(pickRaces([], "2024-01-01")).toEqual({ next: null, last: null });
    expect(pickRaces([rd(1, "2024-03-01", { winner })], "2024-12-01").next).toBeNull();
  });
});

describe("countdownParts", () => {
  it("splits and ends", () => {
    expect(countdownParts(90_061_000, 0)).toEqual({ days: 1, hours: 1, minutes: 1, seconds: 1 });
    expect(countdownParts(1000, 5000)).toBeNull();
  });
});

describe("Countdown", () => {
  afterEach(() => vi.useRealTimers());
  it("ticks once mounted and shows lights out after the target", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2024-01-01T00:00:00Z"));
    render(<Countdown target="2024-01-01T00:00:03Z" />);
    expect(screen.getByRole("timer")).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(4000);
    });
    expect(screen.getByText("Lights out")).toBeInTheDocument();
  });
});

describe("PodiumCards", () => {
  it("shows the three podium finishers with a link to the round", () => {
    const res = (p: number, slug: string, color: string | null) =>
      ({ position: p, position_text: String(p), driver: { slug, name: `N ${slug}`, code: null, number: null }, team: { slug: "t", name: "Team", color }, grid: 1, laps: 50, status: "Finished", time_ms: p === 1 ? 5527123 : 5234, best_lap_ms: null, points: 25, fastest_lap: null, position_change: 0 }) as components["schemas"]["RaceResult"];
    render(<PodiumCards year={2024} round={3} name="Test GP" results={[res(4, "x", null), res(2, "b", "#3671c6"), res(1, "a", "#ff0000"), res(3, "c", null)]} />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(within(items[0]).getByRole("link", { name: "N a" })).toBeInTheDocument();
    expect(within(items[0]).getByText("1:32:07.123")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Full results and analysis/ })).toHaveAttribute("href", "/seasons/2024/3");
  });
});

describe("TopFive", () => {
  it("lists only five rows and links to the full table", () => {
    const standings: Standings = {
      season: 2024,
      after_round: 3,
      rounds: [1, 2, 3],
      results: Array.from({ length: 8 }, (_, i) => ({
        position: i + 1,
        position_text: String(i + 1),
        entity: { id: i, slug: `d${i}`, name: `Driver ${i}`, code: null, nationality: null },
        points: 100 - i,
        wins: 0,
        podiums: 0,
        gap_to_leader: i,
      })),
    };
    render(<TopFive kind="drivers" standings={standings} />);
    expect(screen.getAllByRole("row")).toHaveLength(6);
    expect(screen.getByRole("link", { name: /Full table/ })).toHaveAttribute("href", "/standings/drivers");
  });
});
