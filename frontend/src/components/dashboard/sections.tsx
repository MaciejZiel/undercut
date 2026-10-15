import Link from "next/link";
import type { ReactNode } from "react";
import { connection } from "next/server";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { getCircuit, getRoundResults, type RaceResults } from "@/lib/api/queries";
import { getDashboard } from "./data";
import { NextRaceCard } from "./next-race-card";
import { PodiumCards } from "./podium-cards";
import { ThisDayCard } from "./this-day-card";
import { StandingsSwitch } from "./standings-switch";
import { TopFive } from "./top-five";

/** A failing section shows its own error and leaves the rest of the dashboard intact. */
async function guarded(title: string, render: () => Promise<ReactNode>): Promise<ReactNode> {
  try {
    return await render();
  } catch {
    return <ErrorState title={title} description="Reload the page to try again." />;
  }
}

/** Next race: the weekend, the place and every session in the viewer's time zone. */
export async function NextRaceSection() {
  // Depends on the current time and on live data: render per request, not at build time.
  await connection();
  return guarded("Could not load the race schedule", async () => {
    const { next_race: next } = await getDashboard();
    if (!next || next.round == null) {
      return (
        <EmptyState
          title="No upcoming race"
          description="The calendar has no further rounds."
          action={{ label: "Open the calendar", href: "/calendar" }}
        />
      );
    }
    // The circuit page has the drawing and the records; the weekend is still useful without them.
    const circuit = await getCircuit(next.circuit.slug).catch(() => null);
    return (
      <NextRaceCard
        circuitDetail={circuit}
        year={next.year}
        round={next.round}
        name={next.name}
        date={next.date}
        circuit={next.circuit}
        raceStartUtc={next.race_start_utc}
        sessions={next.sessions}
      />
    );
  });
}

/** The podium of the latest race, from the same cached call. */
export async function LastRaceSection() {
  await connection();
  return guarded("Could not load the latest race", async () => {
    const { last_race: last } = await getDashboard();
    if (!last || last.podium.length === 0) {
      return <EmptyState title="No race results yet" description="The podium of the latest race will show up here." />;
    }
    // Time, laps and points of the podium come from the results; the podium is still shown without them.
    const results =
      last.round != null
        ? await getRoundResults(last.year, last.round, "RACE")
            .then((r) => (r as RaceResults).results)
            .catch(() => null)
        : null;
    return (
      <PodiumCards
        year={last.year}
        round={last.round}
        name={last.name}
        date={last.date}
        podium={last.podium}
        fastestLap={last.fastest_lap}
        results={results}
      />
    );
  });
}

/** One championship panel with a drivers / constructors switch; both tables come from the cached call. */
export async function ChampionshipSection() {
  await connection();
  return guarded("Could not load the standings", async () => {
    const { driver_standings: drivers, constructor_standings: constructors } = await getDashboard();
    if (drivers.entries.length === 0 && constructors.entries.length === 0) {
      return (
        <EmptyState title="No standings yet" description="The tables appear after the first round of the season." />
      );
    }
    return (
      <section aria-labelledby="championship-h">
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 id="championship-h" className="heading text-[1.5rem] sm:text-[1.625rem]">
            Championship{drivers.season ? ` ${drivers.season}` : ""}
          </h2>
          <Link href="/standings/drivers" className="eyebrow whitespace-nowrap hover:text-accent">
            Full standings →
          </Link>
        </div>
        <StandingsSwitch
          season={drivers.season}
          afterRound={drivers.after_round}
          drivers={
            drivers.entries.length > 0 ? (
              <TopFive kind="drivers" standings={drivers} />
            ) : (
              <p className="py-6 text-sm text-muted">No drivers standings yet</p>
            )
          }
          constructors={
            constructors.entries.length > 0 ? (
              <TopFive kind="constructors" standings={constructors} />
            ) : (
              <p className="py-6 text-sm text-muted">No constructors standings yet</p>
            )
          }
        />
      </section>
    );
  });
}

/** A thin strip above the weekend: the season and today's date. The wordmark lives in the header. */
export async function Masthead() {
  await connection();
  let season: number | null = null;
  try {
    season = (await getDashboard()).driver_standings.season ?? null;
  } catch {
    season = null;
  }
  const today = new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" }).format(new Date());
  return (
    <div className="flex items-baseline justify-between gap-4 border-b-4 border-fg pb-2 pt-1">
      <p className="eyebrow">{season ? `Season ${season}` : "Season"}</p>
      <p className="eyebrow">{today}</p>
    </div>
  );
}

/** "On this day": the winner of a race held on today's date in an earlier year. Lives in the archive. */
export async function ThisDaySection() {
  await connection();
  return guarded("Could not load this day in F1", async () => {
    const { this_day_in_f1: item } = await getDashboard();
    return item ? <ThisDayCard item={item} /> : null;
  });
}
