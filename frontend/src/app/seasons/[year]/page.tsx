import { Suspense } from "react";
import type { Metadata } from "next";
import { pageMetadata } from "@/lib/seo";
import { notFound } from "next/navigation";
import Link from "next/link";
import { PageHeader } from "@/components/ui/page-header";
import { DetailPageSkeleton } from "@/components/states/page-skeletons";
import { EmptyState } from "@/components/states/empty-state";
import { StatTiles } from "@/components/ui/stat-tiles";
import { LoadingSkeleton } from "@/components/states/loading-skeleton";
import { SeasonMatrixSection } from "@/components/season/matrix";
import { CalendarTable } from "@/components/catalog/season-tables";
import { getSeason } from "@/lib/api/queries";
import { seasonHref } from "@/lib/routes";
import { parseIntParam } from "@/lib/url";

function parseYear(raw: string) {
  return parseIntParam(raw, { min: 1950, max: 2100 });
}

export async function generateMetadata({ params }: PageProps<"/seasons/[year]">): Promise<Metadata> {
  const year = parseYear((await params).year);
  const season = year ? await getSeason(year) : null;
  if (!season) return { title: "Season not found" };
  return pageMetadata({
    title: `${season.year} season`,
    description: `The ${season.year} Formula 1 calendar with winners of every round.`,
    path: seasonHref(season.year),
  });
}

export default function SeasonPage({ params }: PageProps<"/seasons/[year]">) {
  return (
    <Suspense fallback={<DetailPageSkeleton />}>
      <SeasonDetail params={params} />
    </Suspense>
  );
}

async function SeasonDetail({ params }: { params: PageProps<"/seasons/[year]">["params"] }) {
  const year = parseYear((await params).year);
  const season = year ? await getSeason(year) : null;
  if (!season) notFound();

  const today = new Date().toISOString().slice(0, 10);
  const held = season.rounds.filter((r) => !r.is_cancelled);
  const completed = held.filter((r) => r.winner).length;
  const cancelled = season.rounds.length - held.length;

  return (
    <>
      <PageHeader
        title={`${season.year} season`}
        description={season.name && season.name !== String(season.year) ? season.name : undefined}
        breadcrumbs={[{ label: "Seasons", href: "/seasons" }, { label: String(season.year) }]}
      >
        <nav aria-label="Other seasons" className="mt-3 flex gap-4 text-sm font-semibold">
          {season.year > 1950 && (
            <Link href={seasonHref(season.year - 1)} className="text-muted hover:text-fg">
              <span aria-hidden="true">&larr; </span>
              {season.year - 1}
            </Link>
          )}
          {season.year < Number(today.slice(0, 4)) && (
            <Link href={seasonHref(season.year + 1)} className="text-muted hover:text-fg">
              {season.year + 1}
              <span aria-hidden="true"> &rarr;</span>
            </Link>
          )}
        </nav>
      </PageHeader>
      <StatTiles
        label={`${season.year} season facts`}
        stats={[
          { label: "Rounds", value: String(held.length) },
          { label: "Completed", value: String(completed) },
          { label: "Sprint rounds", value: String(season.sprint_rounds) },
          { label: "Cancelled", value: String(cancelled) },
        ]}
      />
      <section aria-labelledby="calendar-h">
        <h2 id="calendar-h" className="mb-3 heading text-xl sm:text-[1.375rem]">
          Calendar
        </h2>
        {season.rounds.length === 0 ? (
          <EmptyState title="No rounds yet" description="The calendar for this season has not been published." />
        ) : (
          <CalendarTable year={season.year} rounds={season.rounds} today={today} />
        )}
      </section>
      <section aria-labelledby="matrix-h" className="mt-10">
        <h2 id="matrix-h" className="mb-3 heading text-xl sm:text-[1.375rem]">
          Results matrix
        </h2>
        <Suspense fallback={<LoadingSkeleton variant="table" rows={10} label="Loading the results matrix" />}>
          <SeasonMatrixSection year={season.year} />
        </Suspense>
      </section>
    </>
  );
}
