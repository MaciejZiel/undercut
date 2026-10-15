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
          <div>
            <p className="eyebrow mb-1.5">The championship{drivers.season ? ` / ${drivers.season}` : ""}</p>
            <h2 id="championship-h" className="heading text-[1.5rem] sm:text-[1.625rem]">
              Points on the board.
            </h2>
          </div>
          <Link href="/standings/drivers" className="eyebrow whitespace-nowrap hover:text-accent">
            Full standings ↗
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

/** The bottom rule of the page: what happened on this day, and the invitation to call the next podium. */
export async function BottomSection() {
  await connection();
  return guarded("Could not load this day in F1", async () => {
    const { this_day_in_f1: item, next_race: next } = await getDashboard();
    const predict = next && next.round != null ? next : null;
    if (!item && !predict) return null;
    const both = Boolean(item && predict);
    return (
      <div className={`grid grid-cols-1 border-t-[3px] border-fg ${both ? "lg:grid-cols-[minmax(0,1fr)_23.5rem]" : ""}`}>
        {item && <ThisDayCard item={item} />}
        {predict && (
          <section
            aria-labelledby="predict-h"
            className={`py-6 ${both ? "border-t border-fg lg:border-l lg:border-t-0 lg:pl-7" : ""}`}
          >
            <p className="eyebrow">Your call / Round {predict.round}</p>
            <h2 id="predict-h" className="heading mb-3 mt-2 text-[1.3125rem]">
              Who takes the top step?
            </h2>
            <Link
              href="/predict"
              className="t-fast border-b-2 border-accent pb-1.5 text-[0.8125rem] font-bold hover:text-accent"
            >
              Join the prediction grid ↗
            </Link>
          </section>
        )}
      </div>
    );
  });
}

/** The big masthead of the home page: the name, the season and today's date. */
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
    <div className="flex items-end justify-between gap-6 border-b-4 border-fg pb-4 pt-1">
      <p aria-hidden="true" className="display flex shrink-0 items-start whitespace-nowrap text-[clamp(3.2rem,13.5vw,8.25rem)] leading-[0.88]">
        undercut
        <svg viewBox="0 0 24 24" className="ml-[0.04em] mt-[0.08em] size-[0.62em] fill-none stroke-accent" strokeWidth={2.6} strokeLinecap="square">
          <path d="M5 19 19 5M8 5h11v11" />
        </svg>
      </p>
      <p className="ml-auto hidden shrink-0 whitespace-nowrap pb-1 text-xs leading-relaxed 2xl:block">
        Every lap has a story.
        <br />
        Follow the numbers.
      </p>
      <p className="eyebrow ml-auto hidden shrink-0 pb-1 text-right sm:block 2xl:ml-0">
        {season ? `Season ${season}` : "Season"}
        <br />
        {today}
      </p>
    </div>
  );
}
