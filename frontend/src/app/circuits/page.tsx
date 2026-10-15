import { Suspense } from "react";
import type { Metadata } from "next";
import { pageMetadata } from "@/lib/seo";
import { PageHeader } from "@/components/ui/page-header";
import { ListPageSkeleton } from "@/components/states/page-skeletons";
import { EmptyState } from "@/components/states/empty-state";
import { PageOutOfRange } from "@/components/states/out-of-range";
import { FilterForm } from "@/components/ui/filter-form";
import { Pagination } from "@/components/ui/pagination";
import { CircuitsTable } from "@/components/catalog/circuit-tables";
import { getCircuits } from "@/lib/api/queries";
import { buildHref, first, parseChoice, parseIntParam } from "@/lib/url";

export const metadata: Metadata = pageMetadata({
  title: "Circuits",
  description: "Every circuit that hosted a Grand Prix, with the number of races and the latest one.",
  path: "/circuits",
});

const ORDERINGS = ["name", "-name", "country", "-country", "gp_count", "-gp_count", "last_gp_date", "-last_gp_date"] as const;
const PAGE_SIZE = 25;

export default function CircuitsPage({ searchParams }: PageProps<"/circuits">) {
  return (
    <>
      <PageHeader
        title="Circuits"
        description="Every circuit that hosted a Grand Prix."
        breadcrumbs={[{ label: "Catalog", href: "/catalog" }, { label: "Circuits" }]}
      />
      <Suspense fallback={<ListPageSkeleton filters />}>
        <CircuitList searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function CircuitList({ searchParams }: { searchParams: PageProps<"/circuits">["searchParams"] }) {
  const sp = await searchParams;
  const country = first(sp.country);
  const q = first(sp.q);
  const ordering = parseChoice(sp.ordering, ORDERINGS, "name");
  const page = parseIntParam(sp.page) ?? 1;
  const filters = { country, q };
  const sortState = { ...filters, ordering: ordering === "name" ? undefined : ordering };

  const data = await getCircuits({ ...filters, ordering, page, page_size: PAGE_SIZE });

  const form = (
    <FilterForm
      action="/circuits"
      hidden={{ ordering: sortState.ordering }}
      resetHref={buildHref("/circuits", { ordering: sortState.ordering })}
      active={Boolean(country || q)}
      fields={[
        { kind: "text", name: "q", label: "Name or location", value: q ?? "", placeholder: "Search circuits" },
        { kind: "text", name: "country", label: "Country", value: country ?? "", placeholder: "Any" },
      ]}
    />
  );

  if (data === null) {
    return (
      <>
        {form}
        <PageOutOfRange firstPageHref={buildHref("/circuits", sortState)} />
      </>
    );
  }
  return (
    <>
      {form}
      {data.results.length === 0 ? (
        <EmptyState
          title="No circuits match these filters"
          description="Try a different country or clear a filter."
          action={{ label: "Clear filters", href: "/circuits" }}
        />
      ) : (
        <>
          <CircuitsTable circuits={data.results} ordering={ordering} params={sortState} />
          <Pagination path="/circuits" params={sortState} page={page} pageSize={PAGE_SIZE} count={data.count} />
        </>
      )}
    </>
  );
}
