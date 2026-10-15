import Link from "next/link";
import { Suspense } from "react";
import type { Metadata } from "next";
import { pageMetadata } from "@/lib/seo";
import { PageHeader } from "@/components/ui/page-header";
import { ListPageSkeleton } from "@/components/states/page-skeletons";
import { EmptyState } from "@/components/states/empty-state";
import { PageOutOfRange } from "@/components/states/out-of-range";
import { FilterForm } from "@/components/ui/filter-form";
import { Pagination } from "@/components/ui/pagination";
import { DriversTable } from "@/components/catalog/driver-tables";
import { getConstructors, getDrivers, getSeasons } from "@/lib/api/queries";
import { KNOWN_NATIONALITIES } from "@/lib/nationality";
import { buildHref, first, param, parseChoice, parseIntParam, resolveSeasonFilter } from "@/lib/url";

export const metadata: Metadata = pageMetadata({
  title: "Drivers",
  description: "Every driver in the history of the championship: starts, wins, titles and teams.",
  path: "/drivers",
});

const ORDERINGS = ["family_name", "-family_name", "wins", "-wins", "starts", "-starts", "titles", "-titles"] as const;
const PAGE_SIZE = 25;

export default function DriversPage({ searchParams }: PageProps<"/drivers">) {
  return (
    <>
      <PageHeader
        title="Drivers"
        description="Every driver in the history of the championship. Filter by season, nationality or team."
        breadcrumbs={[{ label: "Archive", href: "/catalog" }, { label: "Drivers" }]}
      />
      <Suspense fallback={<ListPageSkeleton filters />}>
        <DriverList searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function DriverList({ searchParams }: { searchParams: PageProps<"/drivers">["searchParams"] }) {
  const sp = await searchParams;
  const nationality = first(sp.nationality);
  const constructor = first(param(sp, "constructor"));
  const q = first(sp.q);
  const latest = (await getSeasons(1))?.results[0]?.year;
  const { season, defaulted } = resolveSeasonFilter({
    season: sp.season,
    latest,
    hasOtherFilters: Boolean(nationality || constructor || q),
  });
  const ordering = parseChoice(sp.ordering, ORDERINGS, "family_name");
  const page = parseIntParam(sp.page) ?? 1;

  const filters = { season, nationality, constructor, q };
  const sortState = { ...filters, ordering: ordering === "family_name" ? undefined : ordering };

  const [data, teams] = await Promise.all([
    getDrivers({ ...filters, ordering, page, page_size: PAGE_SIZE }),
    getConstructors({ season, ordering: "-starts", page_size: 100 }),
  ]);

  const hasFilters = Boolean((season && !defaulted) || nationality || constructor || q);
  const form = (
    <FilterForm
      action="/drivers"
      hidden={{ ordering: sortState.ordering }}
      resetHref={buildHref("/drivers", { ordering: sortState.ordering })}
      active={hasFilters}
      fields={[
        { kind: "text", name: "q", label: "Name", value: q ?? "", placeholder: "Search by name" },
        { kind: "number", name: "season", label: "Season", value: season ? String(season) : "", placeholder: "All seasons", min: 1950, max: 2100 },
        { kind: "text", name: "nationality", label: "Nationality", value: nationality ?? "", placeholder: "Any", list: KNOWN_NATIONALITIES },
        {
          kind: "select",
          name: "constructor",
          label: "Constructor",
          value: constructor ?? "",
          allLabel: "All constructors",
          options: [
            ...(teams?.results ?? []).map((t) => ({ value: t.slug, label: t.name })),
            ...(constructor && !(teams?.results ?? []).some((t) => t.slug === constructor)
              ? [{ value: constructor, label: constructor }]
              : []),
          ].sort((a, b) => a.label.localeCompare(b.label)),
        },
      ]}
    />
  );

  if (data === null) {
    return (
      <>
        {form}
        <PageOutOfRange firstPageHref={buildHref("/drivers", sortState)} />
      </>
    );
  }

  return (
    <>
      {form}
      {defaulted && (
        <p className="text-sm text-muted">
          Showing the {season} season.{" "}
          <Link className="font-semibold underline" href="/drivers?season=all">
            Show every driver in history
          </Link>
        </p>
      )}
      {data.results.length === 0 ? (
        <EmptyState
          title="No drivers match these filters"
          description="Try a different season or clear a filter."
          action={{ label: "Clear filters", href: "/drivers" }}
        />
      ) : (
        <>
          <DriversTable drivers={data.results} ordering={ordering} params={sortState} />
          <Pagination path="/drivers" params={sortState} page={page} pageSize={PAGE_SIZE} count={data.count} />
        </>
      )}
    </>
  );
}
