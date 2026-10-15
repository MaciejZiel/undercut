import type { ReactNode } from "react";
import { connection } from "next/server";
import type { StandingsKind } from "@/lib/api/queries";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { getDashboard } from "./data";
import { NextRaceCard } from "./next-race-card";
import { PodiumCards } from "./podium-cards";
import { ThisDayCard } from "./this-day-card";
import { TopFive } from "./top-five";

/** A failing section shows its own error and leaves the rest of the dashboard intact. */
async function guarded(title: string, render: () => Promise<ReactNode>): Promise<ReactNode> {
  try {
    return await render();
  } catch {
    return <ErrorState title={title} description="Reload the page to try again." />;
  }
}

/** Next race with countdown and the last race podium; both come from the same cached call. */
export async function RaceSections() {
  // Depends on the current time and on live data: render per request, not at build time.
  await connection();
  return guarded("Could not load the race schedule", async () => {
    const { next_race: next, last_race: last } = await getDashboard();
    if (!next && !last) {
      return (
        <EmptyState
          title="No season data yet"
          description="Races appear here as soon as the calendar is imported."
          action={{ label: "Browse seasons", href: "/seasons" }}
        />
      );
    }
    return (
      <div className="flex flex-col gap-14">
        {next && next.round != null ? (
          <NextRaceCard
            year={next.year}
            round={next.round}
            name={next.name}
            date={next.date}
            circuit={next.circuit}
            raceStartUtc={next.race_start_utc}
            sessions={next.sessions}
          />
        ) : (
          <EmptyState
            title="No upcoming race"
            description="The calendar has no further rounds."
            action={{ label: "Open the calendar", href: "/calendar" }}
          />
        )}
        {last && last.podium.length > 0 ? (
          <PodiumCards
            year={last.year}
            round={last.round}
            name={last.name}
            podium={last.podium}
            fastestLap={last.fastest_lap}
          />
        ) : (
          <EmptyState title="No race results yet" description="The podium of the latest race will show up here." />
        )}
      </div>
    );
  });
}

export async function TopFiveSection({ kind }: { kind: StandingsKind }) {
  await connection();
  return guarded(`Could not load the ${kind} standings`, async () => {
    const dashboard = await getDashboard();
    const standings = kind === "drivers" ? dashboard.driver_standings : dashboard.constructor_standings;
    if (standings.entries.length === 0) {
      return (
        <EmptyState
          title={`No ${kind} standings yet`}
          description="The table appears after the first round of the season."
        />
      );
    }
    return <TopFive kind={kind} standings={standings} />;
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
