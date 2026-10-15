import { act, cleanup, render, screen, within } from "@testing-library/react";
import { mockFetch } from "@/test/fetch-mock";
import { ME_ANON, renderWithProviders } from "@/test/render";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { components } from "@/lib/api/client";
import { Countdown } from "./countdown";
import { countdownParts } from "./countdown-parts";
import { PodiumCards } from "./podium-cards";
import { ThisDayCard } from "./this-day-card";
import { TopFive } from "./top-five";

describe("countdownParts", () => {
  it("splits and ends", () => {
    expect(countdownParts(90_061_000, 0)).toEqual({ days: 1, hours: 1, minutes: 1, seconds: 1 });
    expect(countdownParts(1000, 5000)).toBeNull();
  });
});

describe("Countdown", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });
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

const driver = (slug: string) => ({ slug, name: `N ${slug}`, code: null, number: null });

describe("PodiumCards", () => {
  const podium = [
    { position: 3, driver: driver("c"), team: { slug: "t", name: "Team C", color: null } },
    { position: 1, driver: driver("a"), team: { slug: "t", name: "Team A", color: "#ff0000" } },
    { position: 2, driver: driver("b"), team: { slug: "t", name: "Team B", color: "#3671c6" } },
  ];
  it("shows the podium winner first, a link to the round and the fastest lap", () => {
    render(
      <PodiumCards
        year={2024}
        round={3}
        name="Test GP"
        podium={podium}
        fastestLap={{ driver: driver("b"), team: { slug: "t", name: "Team B", color: null }, time_ms: 83456 }}
      />,
    );
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(within(items[0]).getByRole("link", { name: "N a" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Full results and analysis/ })).toHaveAttribute("href", "/seasons/2024/3");
    expect(screen.getByText("1:23.456")).toBeInTheDocument();
  });
  it("shows a dash instead of an unknown fastest lap and hides the link without a round", () => {
    render(<PodiumCards year={2024} round={null} name="Test GP" podium={podium} fastestLap={null} />);
    expect(screen.queryByRole("link", { name: /Full results/ })).not.toBeInTheDocument();
    expect(screen.getByText(/Fastest lap:/)).toHaveTextContent("Fastest lap: —Not available");
  });
});

describe("TopFive", () => {
  const standings = (n: number): components["schemas"]["TopStandings"] => ({
    season: 2024,
    after_round: 3,
    entries: Array.from({ length: n }, (_, i) => ({
      position: i + 1,
      slug: `d${i}`,
      name: `Driver ${i}`,
      code: null,
      color: "#ff0000",
      team_name: null,
      points: 100 - i,
      wins: 0,
    })),
  });
  it("lists only five rows and links to the full table", () => {
    render(<TopFive kind="drivers" standings={standings(8)} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(5);
    expect(screen.getByRole("link", { name: /Full table/ })).toHaveAttribute("href", "/standings/drivers");
  });
  it("shows each driver's team and how far behind the leader", () => {
    const rows = standings(2);
    rows.entries[0] = { ...rows.entries[0], team_name: "Mercedes" };
    render(<TopFive kind="drivers" standings={rows} />);
    expect(screen.getByText("Mercedes")).toBeInTheDocument();
    expect(screen.getByText("−1")).toBeInTheDocument();
  });
  it("links constructors to their pages", () => {
    render(<TopFive kind="constructors" standings={standings(2)} />);
    expect(screen.getByRole("link", { name: "Driver 0" })).toHaveAttribute("href", "/constructors/d0");
  });
});

describe("ThisDayCard", () => {
  it("names the winner and links the round", () => {
    render(<ThisDayCard item={{ year: 1988, round: 5, race: "Mexican Grand Prix", date: "1988-05-15", driver: driver("a"), team: { slug: "t", name: "McLaren", color: null } }} />);
    expect(screen.getByText(/On this day/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "1988 Mexican Grand Prix" })).toHaveAttribute("href", "/seasons/1988/5");
  });
});

type Dashboard = components["schemas"]["Dashboard"];
const getDashboard = vi.fn<() => Promise<Dashboard>>();
vi.mock("./data", () => ({ getDashboard: () => getDashboard() }));
vi.mock("next/server", () => ({ connection: async () => {} }));

const base: Dashboard = {
  next_race: null,
  last_race: null,
  driver_standings: { season: null, after_round: null, entries: [] },
  constructor_standings: { season: null, after_round: null, entries: [] },
  this_day_in_f1: null,
  counts: { seasons: 1, races: 2, drivers: 3 },
};

describe("dashboard sections", () => {
  it("shows empty states when there is no data", async () => {
    getDashboard.mockResolvedValue(base);
    const { NextRaceSection, LastRaceSection, ChampionshipSection, ThisDaySection } = await import("./sections");
    render(await NextRaceSection());
    expect(screen.getByText("No upcoming race")).toBeInTheDocument();
    cleanup();
    render(await LastRaceSection());
    expect(screen.getByText("No race results yet")).toBeInTheDocument();
    cleanup();
    render(await ChampionshipSection());
    expect(screen.getByText("No standings yet")).toBeInTheDocument();
    cleanup();
    expect(await ThisDaySection()).toBeNull();
  });
  it("shows the next race and the podium", async () => {
    getDashboard.mockResolvedValue({
      ...base,
      next_race: {
        year: 2025, round: 4, name: "Next GP", date: "2025-04-20", status: "next", is_next: true, has_sprint: false,
        race_start_utc: "2099-01-01T00:00:00Z", circuit: { slug: "c", name: "Circuit", country: "Spain", locality: null, timezone: null },
        sessions: [], winner: null,
      },
      last_race: {
        year: 2025,
        round: 3,
        name: "Last GP",
        date: "2025-04-01",
        circuit: { slug: "c", name: "Circuit", country: null },
        podium: [{ position: 1, driver: driver("a"), team: { slug: "t", name: "Team", color: null } }],
        fastest_lap: null,
      },
    });
    mockFetch({ "GET /api/v1/auth/me/": { body: ME_ANON } });
    const { NextRaceSection, LastRaceSection } = await import("./sections");
    renderWithProviders((await NextRaceSection()) as ReactElement);
    expect(screen.getByRole("link", { name: "Next GP" })).toHaveAttribute("href", "/seasons/2025/4");
    cleanup();
    renderWithProviders((await LastRaceSection()) as ReactElement);
    expect(screen.getByRole("link", { name: "N a" })).toBeInTheDocument();
    cleanup();
    renderWithProviders((await NextRaceSection()) as ReactElement);
    expect(screen.getByRole("link", { name: "Download the file (.ics)" })).toHaveAttribute(
      "href",
      "/api/v1/calendar/ics/?year=2025&round=4",
    );
  });
  it("keeps the error inside the section", async () => {
    getDashboard.mockRejectedValue(new Error("down"));
    const { ChampionshipSection } = await import("./sections");
    render(await ChampionshipSection());
    expect(screen.getByRole("alert")).toHaveTextContent("Could not load the standings");
  });
});
