import Link from "next/link";
import type { ReactNode } from "react";
import { connection } from "next/server";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { getCircuit } from "@/lib/api/queries";
import { getDashboard } from "./data";
import { NextRaceCard } from "./next-race-card";
import { PodiumCards } from "./podium-cards";
import { ThisDayCard } from "./this-day-card";
import { ArchiveLinks } from "./archive-links";
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
    return (
      <PodiumCards
        year={last.year}
        round={last.round}
        name={last.name}
        date={last.date}
        podium={last.podium}
        fastestLap={last.fastest_lap}
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
        <p className="text-sm font-bold text-accent">{drivers.season ? `${drivers.season} season` : "Season"}</p>
        <h2 id="championship-h" className="heading mb-5 mt-2 text-xl sm:text-[1.375rem]">
          The championship
        </h2>
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

/** An invitation to the prediction game for the coming race; the only warm colour on the page. */
export async function PredictionInvite() {
  await connection();
  return guarded("Could not load the prediction invitation", async () => {
    const { next_race: next } = await getDashboard();
    if (!next || next.round == null) return null;
    return (
      <section aria-labelledby="predict-h" className="flex flex-col gap-5 rounded-xl bg-flag p-6 text-on-flag sm:flex-row sm:items-center sm:justify-between sm:px-9 sm:py-7">
        <div>
          <h2 id="predict-h" className="heading text-xl sm:text-[1.375rem]">
            Who is on your {next.name.replace(/ Grand Prix$/, "")} podium?
          </h2>
          <p className="mt-2 text-sm">Pick your top three before qualifying starts.</p>
        </div>
        <Link
          href="/predict"
          className="t-fast inline-flex min-h-11 shrink-0 items-center justify-center rounded-md bg-fg px-5 py-2.5 text-sm font-bold text-bg hover:opacity-90"
        >
          Make a prediction
        </Link>
      </section>
    );
  });
}

/** Renders nothing when no race was won on today's date in an earlier year. */
export async function ThisDaySection() {
  await connection();
  return guarded("Could not load this day in F1", async () => {
    const { this_day_in_f1: item } = await getDashboard();
    return item ? <ThisDayCard item={item} /> : null;
  });
}

/** The archive entry point with the size of the archive from the cached call; the links work even when the call fails. */
export async function ArchiveSection() {
  await connection();
  let counts: { seasons: number; races: number; drivers: number } | null = null;
  try {
    counts = (await getDashboard()).counts;
  } catch {
    counts = null;
  }
  return <ArchiveLinks counts={counts} />;
}
