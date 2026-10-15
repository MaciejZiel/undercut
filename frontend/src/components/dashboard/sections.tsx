import type { ReactNode } from "react";
import { connection } from "next/server";
import {
  getRound,
  getRoundResults,
  getSeason,
  getSeasons,
  getStandings,
  type RaceResults,
  type StandingsKind,
} from "@/lib/api/queries";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { NextRaceCard } from "./next-race-card";
import { PodiumCards } from "./podium-cards";
import { pickRaces } from "./pick-races";
import { TopFive } from "./top-five";

/** A failing section shows its own error and leaves the rest of the dashboard intact. */
async function guarded(title: string, render: () => Promise<ReactNode>): Promise<ReactNode> {
  try {
    return await render();
  } catch {
    return <ErrorState title={title} description="Reload the page to try again." />;
  }
}

/** Latest season that exists in the catalog. */
async function latestSeasonYear(): Promise<number | null> {
  const seasons = await getSeasons(1);
  const years = (seasons?.results ?? []).map((s) => s.year);
  return years.length ? Math.max(...years) : null;
}

/** Next race with countdown and last race podium share one season lookup (cached). */
export async function RaceSections() {
  // Depends on the current time and on live data: render per request, not at build time.
  await connection();
  return guarded("Could not load the race schedule", async () => {
    const year = await latestSeasonYear();
    const season = year ? await getSeason(year) : null;
    if (!year || !season || season.rounds.length === 0) {
      return (
        <EmptyState
          title="No season data yet"
          description="Races appear here as soon as the calendar is imported."
          action={{ label: "Browse seasons", href: "/seasons" }}
        />
      );
    }
    const today = new Date().toISOString().slice(0, 10);
    const { next, last } = pickRaces(season.rounds, today);

    const nextDetail = next?.round ? await getRound(year, next.round) : null;
    const raceStart = nextDetail?.sessions.find((s) => s.type === "RACE")?.start_utc ?? null;
    const lastResults = last?.round ? ((await getRoundResults(year, last.round, "RACE")) as RaceResults | null) : null;

    return (
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <div>
          {next && next.round ? (
            <NextRaceCard
              year={year}
              round={next.round}
              name={next.name}
              date={next.date}
              circuit={next.circuit}
              raceStartUtc={raceStart}
            />
          ) : (
            <EmptyState
              title="No upcoming race"
              description={`The ${year} calendar has no further rounds.`}
              action={{ label: "Open the calendar", href: `/seasons/${year}` }}
            />
          )}
        </div>
        <div>
          {last && last.round && lastResults && lastResults.results.length > 0 ? (
            <PodiumCards year={year} round={last.round} name={last.name} results={lastResults.results} />
          ) : (
            <EmptyState title="No race results yet" description="The podium of the latest race will show up here." />
          )}
        </div>
      </div>
    );
  });
}

export async function TopFiveSection({ kind }: { kind: StandingsKind }) {
  await connection();
  return guarded(`Could not load the ${kind} standings`, async () => {
    const standings = await getStandings(kind);
    if (!standings || standings.results.length === 0) {
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
