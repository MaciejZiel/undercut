import { Suspense } from "react";
import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/page-header";
import { LoadingSkeleton } from "@/components/states/loading-skeleton";
import { CompareView } from "@/components/compare/compare-view";
import { parseSeason, parseSlug } from "@/components/compare/compare-url";

export const metadata: Metadata = {
  title: "Compare drivers",
  description: "Two Formula 1 drivers side by side: career statistics and head to head.",
};

export default function ComparePage({ searchParams }: PageProps<"/compare">) {
  return (
    <>
      <PageHeader
        title="Compare drivers"
        description="Put two drivers side by side: career statistics and who finished ahead."
        breadcrumbs={[{ label: "Drivers", href: "/drivers" }, { label: "Compare" }]}
      />
      <Suspense fallback={<LoadingSkeleton variant="table" rows={7} label="Loading the comparison" />}>
        <CompareContent searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function CompareContent({ searchParams }: { searchParams: PageProps<"/compare">["searchParams"] }) {
  const sp = await searchParams;
  return <CompareView initial={{ a: parseSlug(sp.a), b: parseSlug(sp.b), season: parseSeason(sp.season) }} />;
}
