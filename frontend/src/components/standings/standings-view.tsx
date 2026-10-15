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

  const tabs = (
    <nav aria-label="Championship" className="mb-6 overflow-x-auto overflow-y-hidden">
      <ul className="flex gap-1 border-b border-line">
        {(["drivers", "constructors"] as const).map((k) => (
          <li key={k}>
            <Link
              href={buildHref(COPY[k].path, { season, after_round: afterRound })}
              aria-current={k === kind ? "page" : undefined}
              className={`t-fast block whitespace-nowrap border-b-[3px] px-3.5 py-2.5 text-sm font-bold ${
                k === kind ? "border-accent text-accent" : "border-transparent text-muted hover:text-accent"
              }`}
            >
              {k === "drivers" ? "Drivers" : "Constructors"}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );

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
          value: String(season ?? resolvedSeason ?? ""),
          allLabel: "Latest season",
          options: [...years].sort((a, b) => b - a).map((y) => ({ value: String(y), label: String(y) })),
        },
        {
          kind: "select",
          name: "after_round",
          label: "After round",
          value: String(afterRound ?? (season ? "" : (data?.after_round ?? ""))),
          allLabel: "Latest round",
          options: rounds.map((r) => ({ value: String(r), label: `Round ${r}` })),
        },
      ]}
    />
  );

  if (data === null) {
    return (
      <>
        {tabs}
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

  return (
    <>
      {tabs}
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
            <h2 id="table-h" className="mb-3 heading text-xl sm:text-[1.375rem]">
              {heading}
            </h2>
            <StandingsTable kind={kind} rows={data.results} caption={`${copy.title}: ${heading}`} />
          </section>
          <section aria-labelledby="chart-h">
            <h2 id="chart-h" className="mb-3 heading text-xl sm:text-[1.375rem]">
              Points progression
            </h2>
            <PointsChart kind={kind} season={data.season} />
          </section>
        </>
      )}
    </>
  );
}
