import { Suspense } from "react";
import type { Metadata } from "next";
import { pageMetadata } from "@/lib/seo";
import { constructorHref } from "@/lib/routes";
import { notFound } from "next/navigation";
import { DetailPageSkeleton } from "@/components/states/page-skeletons";
import { EmptyState } from "@/components/states/empty-state";
import { EntityHeader } from "@/components/ui/entity-header";
import { DriverLink, Nationality } from "@/components/ui/entity-links";
import { StatTiles } from "@/components/ui/stat-tiles";
import { ConstructorSeasonsTable } from "@/components/catalog/constructor-tables";
import { getConstructor } from "@/lib/api/queries";
import { formatInteger, formatPoints } from "@/lib/format";
import { isSlug } from "@/lib/url";
import { FavoriteButton } from "@/components/account/favorite-button";

export async function generateMetadata({ params }: PageProps<"/constructors/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const team = isSlug(slug) ? await getConstructor(slug) : null;
  if (!team) return { title: "Constructor not found" };
  return pageMetadata({
    title: team.name,
    description: `${team.name}: wins, season by season results and drivers.`,
    path: constructorHref(slug),
  });
}

export default function ConstructorPage({ params }: PageProps<"/constructors/[slug]">) {
  return (
    <Suspense fallback={<DetailPageSkeleton />}>
      <ConstructorDetail params={params} />
    </Suspense>
  );
}

async function ConstructorDetail({ params }: { params: PageProps<"/constructors/[slug]">["params"] }) {
  const { slug } = await params;
  const team = isSlug(slug) ? await getConstructor(slug) : null;
  if (!team) notFound();

  const { stats } = team;
  const seasons = [...team.seasons].sort((a, b) => b.year - a.year);
  const latestColor = seasons.find((s) => s.color)?.color ?? null;

  return (
    <>
      <EntityHeader
        title={team.name}
        accentColor={latestColor}
        breadcrumbs={[{ label: "Constructors", href: "/constructors" }, { label: team.name }]}
        subtitle={<Nationality value={team.nationality} />}
      >
        {/* Favourites: minimal hook-in, see components/account/favorite-button.tsx */}
        <FavoriteButton kind="constructor" slug={team.slug} name={team.name} />
      </EntityHeader>
      <StatTiles
        label={`${team.name} statistics`}
        stats={[
          { label: "Starts", value: formatInteger(stats.starts) },
          { label: "Wins", value: formatInteger(stats.wins) },
          { label: "Podiums", value: formatInteger(stats.podiums) },
          { label: "Pole positions", value: formatInteger(stats.poles) },
          { label: "Fastest laps", value: formatInteger(stats.fastest_laps) },
          { label: "Titles", value: formatInteger(stats.titles), hint: "Not available yet" },
          { label: "Points", value: formatPoints(stats.points) },
          { label: "Latest season", value: team.current_season },
        ]}
      />
      {team.current_drivers.length > 0 && (
        <section aria-labelledby="line-up-h" className="mb-10">
          <h2 id="line-up-h" className="mb-3 text-xl font-extrabold tracking-tight">
            {team.current_season ? `${team.current_season} line-up` : "Line-up"}
          </h2>
          <ul className="flex flex-wrap gap-x-6 gap-y-2 rounded-lg border border-line bg-surface p-4">
            {team.current_drivers.map((d) => (
              <li key={d.slug}>
                <DriverLink slug={d.slug} name={d.name} />
                {d.number != null && <span className="timing ml-2 text-muted">#{d.number}</span>}
              </li>
            ))}
          </ul>
        </section>
      )}
      <section aria-labelledby="seasons-h">
        <h2 id="seasons-h" className="mb-3 text-xl font-extrabold tracking-tight">
          Seasons
        </h2>
        {seasons.length === 0 ? (
          <EmptyState title="No seasons yet" description="This team has no recorded race entries." />
        ) : (
          <ConstructorSeasonsTable seasons={seasons} />
        )}
      </section>
    </>
  );
}
