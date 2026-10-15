import { Suspense } from "react";
import type { Metadata } from "next";
import { pageMetadata } from "@/lib/seo";
import { circuitHref } from "@/lib/routes";
import { notFound } from "next/navigation";
import { DetailPageSkeleton } from "@/components/states/page-skeletons";
import { EmptyState } from "@/components/states/empty-state";
import { EntityHeader } from "@/components/ui/entity-header";
import { ConstructorLink, DriverLink, Nationality } from "@/components/ui/entity-links";
import { StatTiles } from "@/components/ui/stat-tiles";
import { CircuitWinnersTable, MostWinsList } from "@/components/catalog/circuit-tables";
import { getCircuit } from "@/lib/api/queries";
import { formatDate, formatInteger, formatLapTime, formatLength } from "@/lib/format";
import { isSlug } from "@/lib/url";

export async function generateMetadata({ params }: PageProps<"/circuits/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const circuit = isSlug(slug) ? await getCircuit(slug) : null;
  if (!circuit) return { title: "Circuit not found" };
  return pageMetadata({
    title: circuit.name,
    description: `${circuit.name}${circuit.country ? `, ${circuit.country}` : ""}: every Grand Prix winner and the record holders.`,
    path: circuitHref(slug),
  });
}

export default function CircuitPage({ params }: PageProps<"/circuits/[slug]">) {
  return (
    <Suspense fallback={<DetailPageSkeleton />}>
      <CircuitDetail params={params} />
    </Suspense>
  );
}

function OsmMap({ lat, lng, name }: { lat: number; lng: number; name: string }) {
  const d = 0.02;
  const bbox = [lng - d, lat - d, lng + d, lat + d].map((n) => n.toFixed(5)).join("%2C");
  const src = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat.toFixed(5)}%2C${lng.toFixed(5)}`;
  return (
    <section aria-labelledby="map-h" className="mb-10">
      <h2 id="map-h" className="mb-3 text-xl font-extrabold tracking-tight">
        Location
      </h2>
      <iframe
        title={`Map of ${name}`}
        src={src}
        loading="lazy"
        referrerPolicy="no-referrer"
        className="h-72 w-full rounded-lg border border-line bg-surface-2"
      />
      <p className="mt-2 text-sm text-muted">
        <a
          className="underline underline-offset-2 hover:text-fg"
          href={`https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=15/${lat}/${lng}`}
          rel="noopener noreferrer"
        >
          View larger map
        </a>{" "}
        (OpenStreetMap contributors)
      </p>
    </section>
  );
}

async function CircuitDetail({ params }: { params: PageProps<"/circuits/[slug]">["params"] }) {
  const { slug } = await params;
  const c = isSlug(slug) ? await getCircuit(slug) : null;
  if (!c) notFound();

  const lapRecord = formatLapTime(c.lap_record_ms);

  return (
    <>
      <EntityHeader
        title={c.name}
        breadcrumbs={[{ label: "Circuits", href: "/circuits" }, { label: c.name }]}
        subtitle={<Nationality value={c.country} />}
      >
        {c.locality && <p className="mt-3 text-muted">{c.locality}</p>}
      </EntityHeader>
      <StatTiles
        label={`${c.name} facts`}
        stats={[
          { label: "Grands Prix", value: formatInteger(c.gp_count) },
          { label: "Last Grand Prix", value: formatDate(c.last_gp_date) },
          { label: "Lap length", value: formatLength(c.length_m) },
          {
            label: "Lap record",
            value: lapRecord ? (
              <span>
                {lapRecord}
                {(c.lap_record_driver || c.lap_record_year) && (
                  <span className="block text-sm font-normal text-muted">
                    {[c.lap_record_driver, c.lap_record_year].filter(Boolean).join(", ")}
                  </span>
                )}
              </span>
            ) : null,
          },
        ]}
      />
      {c.lat != null && c.lng != null && <OsmMap lat={c.lat} lng={c.lng} name={c.name} />}
      <section aria-labelledby="records-h" className="mb-10">
        <h2 id="records-h" className="mb-3 text-xl font-extrabold tracking-tight">
          Most wins
        </h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <MostWinsList
            title="Drivers"
            items={c.most_wins_drivers.map((d) => ({
              key: d.slug,
              wins: d.wins,
              node: <DriverLink slug={d.slug} name={d.name} />,
            }))}
          />
          <MostWinsList
            title="Constructors"
            items={c.most_wins_teams.map((t) => ({
              key: t.slug,
              wins: t.wins,
              node: <ConstructorLink slug={t.slug} name={t.name} color={t.color} />,
            }))}
          />
        </div>
      </section>
      <section aria-labelledby="winners-h">
        <h2 id="winners-h" className="mb-3 text-xl font-extrabold tracking-tight">
          Winners
        </h2>
        {c.winners.length === 0 ? (
          <EmptyState title="No winners yet" description="No Grand Prix has been completed at this circuit." />
        ) : (
          <CircuitWinnersTable winners={c.winners} />
        )}
      </section>
    </>
  );
}
