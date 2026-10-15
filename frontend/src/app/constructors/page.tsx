import { Suspense } from "react";
import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/page-header";
import { ListPageSkeleton } from "@/components/states/page-skeletons";
import { EmptyState } from "@/components/states/empty-state";
import { PageOutOfRange } from "@/components/states/out-of-range";
import { FilterForm } from "@/components/ui/filter-form";
import { Pagination } from "@/components/ui/pagination";
import { ConstructorsTable } from "@/components/catalog/constructor-tables";
import { getConstructors } from "@/lib/api/queries";
import { KNOWN_NATIONALITIES } from "@/lib/nationality";
import { buildHref, first, parseChoice, parseIntParam } from "@/lib/url";

export const metadata: Metadata = {
  title: "Constructors",
  description: "Every team in the history of the championship: starts, wins and titles.",
};

const ORDERINGS = ["name", "-name", "wins", "-wins", "starts", "-starts"] as const;
const PAGE_SIZE = 25;

export default function ConstructorsPage({ searchParams }: PageProps<"/constructors">) {
  return (
    <>
      <PageHeader
        title="Constructors"
        description="Every team in the history of the championship."
        breadcrumbs={[{ label: "Catalog", href: "/catalog" }, { label: "Constructors" }]}
      />
      <Suspense fallback={<ListPageSkeleton filters />}>
        <ConstructorList searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function ConstructorList({ searchParams }: { searchParams: PageProps<"/constructors">["searchParams"] }) {
  const sp = await searchParams;
  const season = parseIntParam(sp.season, { min: 1950, max: 2100 });
  const nationality = first(sp.nationality);
  const q = first(sp.q);
  const ordering = parseChoice(sp.ordering, ORDERINGS, "name");
  const page = parseIntParam(sp.page) ?? 1;
  const filters = { season, nationality, q };
  const sortState = { ...filters, ordering: ordering === "name" ? undefined : ordering };

  const data = await getConstructors({ ...filters, ordering, page, page_size: PAGE_SIZE });

  const form = (
    <FilterForm
      action="/constructors"
      hidden={{ ordering: sortState.ordering }}
      resetHref={buildHref("/constructors", { ordering: sortState.ordering })}
      active={Boolean(season || nationality || q)}
      fields={[
        { kind: "text", name: "q", label: "Name", value: q ?? "", placeholder: "Search by name" },
        { kind: "number", name: "season", label: "Season", value: season ? String(season) : "", placeholder: "All seasons", min: 1950, max: 2100 },
        { kind: "text", name: "nationality", label: "Nationality", value: nationality ?? "", placeholder: "Any", list: KNOWN_NATIONALITIES },
      ]}
    />
  );

  if (data === null) {
    return (
      <>
        {form}
        <PageOutOfRange firstPageHref={buildHref("/constructors", sortState)} />
      </>
    );
  }
  return (
    <>
      {form}
      {data.results.length === 0 ? (
        <EmptyState
          title="No constructors match these filters"
          description="Try a different season or clear a filter."
          action={{ label: "Clear filters", href: "/constructors" }}
        />
      ) : (
        <>
          <ConstructorsTable constructors={data.results} ordering={ordering} params={sortState} />
          <Pagination path="/constructors" params={sortState} page={page} pageSize={PAGE_SIZE} count={data.count} />
        </>
      )}
    </>
  );
}
