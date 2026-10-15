import { Suspense } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/ui/page-header";
import { FilterForm } from "@/components/ui/filter-form";
import { EmptyState } from "@/components/states/empty-state";
import { ListPageSkeleton } from "@/components/states/page-skeletons";
import { getSeasons, getStandings, type StandingsKind } from "@/lib/api/queries";
import { seasonHref } from "@/lib/routes";
import { buildHref, parseIntParam, type SearchParams } from "@/lib/url";
import { PointsChart } from "./points-chart";
import { StandingsTable } from "./standings-table";

const COPY = {
  drivers: { title: "Driver standings", path: "/standings/drivers", noun: "drivers" },
  constructors: { title: "Constructor standings", path: "/standings/constructors", noun: "constructors" },
} as const;

export function StandingsPage({
  kind,
  searchParams,
}: {
  kind: StandingsKind;
  searchParams: Promise<SearchParams>;
}) {
  const copy = COPY[kind];
  return (
    <>
      <PageHeader
        title={copy.title}
        description={`The ${copy.noun}' championship table for any season, after any round.`}
        breadcrumbs={[{ label: "Standings" }, { label: copy.title }]}
      />
      <Suspense fallback={<ListPageSkeleton filters rows={12} />}>
        <StandingsContent kind={kind} searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function StandingsContent({ kind, searchParams }: { kind: StandingsKind; searchParams: Promise<SearchParams> }) {
  const copy = COPY[kind];
  const sp = await searchParams;
  const season = parseIntParam(sp.season, { min: 1950, max: 2100 });
  const afterRound = parseIntParam(sp.after_round, { min: 1, max: 100 });

  const [data, seasons] = await Promise.all([getStandings(kind, season, afterRound), getSeasons(1)]);

  const years = new Set((seasons?.results ?? []).map((s) => s.year));
  if (season) years.add(season);
  const resolvedSeason = data?.season ?? season ?? null;
  if (resolvedSeason) years.add(resolvedSeason);
  const rounds = data?.rounds ?? [];

  const form = (
    <FilterForm
      action={copy.path}
      resetHref={copy.path}
      active={Boolean(season || afterRound)}
      fields={[
        {
          kind: "select",
          name: "season",
          label: "Season",
          value: season ? String(season) : "",
          allLabel: "Latest season",
          options: [...years].sort((a, b) => b - a).map((y) => ({ value: String(y), label: String(y) })),
        },
        {
          kind: "select",
          name: "after_round",
          label: "After round",
          value: afterRound ? String(afterRound) : "",
          allLabel: "Latest round",
          options: rounds.map((r) => ({ value: String(r), label: `Round ${r}` })),
        },
      ]}
    />
  );

  if (data === null) {
    return (
      <>
        {form}
        <EmptyState
          title="No standings for this selection"
          description="That season or round has no championship table. Pick another round or go back to the latest one."
          action={{ label: "Show latest standings", href: copy.path }}
        />
      </>
    );
  }

  const heading = data.season
    ? `${data.season} season${data.after_round ? `, after round ${data.after_round}` : ""}`
    : "Standings";
  const other: StandingsKind = kind === "drivers" ? "constructors" : "drivers";

  return (
    <>
      {form}
      {data.results.length === 0 || data.season === null ? (
        <EmptyState
          title="No standings yet"
          description="The championship table appears after the first round of the season."
          action={{ label: "Open the calendar", href: data.season ? seasonHref(data.season) : "/seasons" }}
        />
      ) : (
        <>
          <section aria-labelledby="table-h" className="mb-10">
            <h2 id="table-h" className="mb-3 text-xl font-extrabold tracking-tight">
              {heading}
            </h2>
            <StandingsTable kind={kind} rows={data.results} caption={`${copy.title}: ${heading}`} />
            <p className="mt-3 text-sm">
              <Link
                href={buildHref(COPY[other].path, { season: data.season, after_round: data.after_round })}
                className="font-semibold text-muted hover:text-accent hover:underline"
              >
                See the {COPY[other].noun}&apos; championship &rarr;
              </Link>
            </p>
          </section>
          <section aria-labelledby="chart-h">
            <h2 id="chart-h" className="mb-3 text-xl font-extrabold tracking-tight">
              Points progression
            </h2>
            <PointsChart kind={kind} season={data.season} />
          </section>
        </>
      )}
    </>
  );
}
