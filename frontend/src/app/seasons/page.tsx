import { Suspense } from "react";
import type { Metadata } from "next";
import { pageMetadata } from "@/lib/seo";
import { PageHeader } from "@/components/ui/page-header";
import { ListPageSkeleton } from "@/components/states/page-skeletons";
import { EmptyState } from "@/components/states/empty-state";
import { PageOutOfRange } from "@/components/states/out-of-range";
import { Pagination } from "@/components/ui/pagination";
import { SeasonsTable } from "@/components/catalog/season-tables";
import { getSeasons } from "@/lib/api/queries";
import { parseIntParam } from "@/lib/url";

export const metadata: Metadata = pageMetadata({
  title: "Seasons",
  description: "Every Formula 1 season since 1950 with its champions and number of rounds.",
  path: "/seasons",
});

const PAGE_SIZE = 100;

export default function SeasonsPage({ searchParams }: PageProps<"/seasons">) {
  return (
    <>
      <PageHeader
        title="Seasons"
        description="Year by year, newest first."
        breadcrumbs={[{ label: "Catalog", href: "/catalog" }, { label: "Seasons" }]}
      />
      <Suspense fallback={<ListPageSkeleton filters={false} />}>
        <SeasonList searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function SeasonList({ searchParams }: { searchParams: PageProps<"/seasons">["searchParams"] }) {
  const page = parseIntParam((await searchParams).page) ?? 1;
  const data = await getSeasons(page);
  if (data === null) return <PageOutOfRange firstPageHref="/seasons" />;
  if (data.results.length === 0) {
    return (
      <EmptyState
        title="No seasons yet"
        description="The season history has not been imported."
        action={{ label: "Back to the home page", href: "/" }}
      />
    );
  }
  return (
    <>
      <SeasonsTable seasons={data.results} />
      <Pagination path="/seasons" params={{}} page={page} pageSize={PAGE_SIZE} count={data.count} />
    </>
  );
}
