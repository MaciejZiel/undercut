import { Suspense } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { DetailPageSkeleton } from "@/components/states/page-skeletons";
import { EmptyState } from "@/components/states/empty-state";
import { EntityHeader } from "@/components/ui/entity-header";
import { ConstructorLink, Nationality } from "@/components/ui/entity-links";
import { StatTiles } from "@/components/ui/stat-tiles";
import { DriverLastResultsTable, DriverSeasonsTable } from "@/components/catalog/driver-tables";
import { getDriver } from "@/lib/api/queries";
import { formatDate, formatInteger, formatPoints, fullName } from "@/lib/format";
import { isSlug } from "@/lib/url";

export async function generateMetadata({ params }: PageProps<"/drivers/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const driver = isSlug(slug) ? await getDriver(slug) : null;
  if (!driver) return { title: "Driver not found" };
  const name = fullName(driver);
  return {
    title: name,
    description: `${name}: career statistics, season by season results and latest races.`,
  };
}

export default function DriverPage({ params }: PageProps<"/drivers/[slug]">) {
  return (
    <Suspense fallback={<DetailPageSkeleton />}>
      <DriverDetail params={params} />
    </Suspense>
  );
}

async function DriverDetail({ params }: { params: PageProps<"/drivers/[slug]">["params"] }) {
  const { slug } = await params;
  const driver = isSlug(slug) ? await getDriver(slug) : null;
  if (!driver) notFound();

  const name = fullName(driver);
  const { stats } = driver;
  const seasons = [...driver.seasons].sort((a, b) => b.year - a.year);

  return (
    <>
      <EntityHeader
        title={name}
        accentColor={driver.team?.color}
        breadcrumbs={[{ label: "Drivers", href: "/drivers" }, { label: name }]}
        subtitle={
          <>
            <Nationality value={driver.nationality} />
            {driver.date_of_birth && <span>Born {formatDate(driver.date_of_birth)}</span>}
            {driver.number != null && <span className="timing">#{driver.number}</span>}
            {driver.code && <span className="timing">{driver.code}</span>}
          </>
        }
      />
      <StatTiles
        label={`${name} career statistics`}
        stats={[
          { label: "Starts", value: formatInteger(stats.starts) },
          { label: "Wins", value: formatInteger(stats.wins) },
          { label: "Podiums", value: formatInteger(stats.podiums) },
          { label: "Pole positions", value: formatInteger(stats.poles) },
          { label: "Fastest laps", value: formatInteger(stats.fastest_laps) },
          { label: "Titles", value: formatInteger(stats.titles), hint: "Not available yet" },
          { label: "Career points", value: formatPoints(stats.points) },
          {
            label: "Current or last team",
            value: driver.team ? <span className="text-base"><ConstructorLink {...driver.team} /></span> : null,
          },
        ]}
      />
      <section aria-labelledby="seasons-h" className="mb-10">
        <h2 id="seasons-h" className="mb-3 text-xl font-extrabold tracking-tight">
          Seasons
        </h2>
        {seasons.length === 0 ? (
          <EmptyState title="No seasons yet" description="This driver has no recorded race entries." />
        ) : (
          <DriverSeasonsTable seasons={seasons} />
        )}
      </section>
      <section aria-labelledby="last-h">
        <h2 id="last-h" className="mb-3 text-xl font-extrabold tracking-tight">
          Last results
        </h2>
        {driver.last_results.length === 0 ? (
          <EmptyState title="No results yet" description="Race results will appear here once they are imported." />
        ) : (
          <DriverLastResultsTable results={driver.last_results} />
        )}
      </section>
    </>
  );
}
