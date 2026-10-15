import { Suspense } from "react";
import type { Metadata } from "next";
import { pageMetadata } from "@/lib/seo";
import { circuitHref } from "@/lib/routes";
import { notFound } from "next/navigation";
import { DetailPageSkeleton } from "@/components/states/page-skeletons";
import { EmptyState } from "@/components/states/empty-state";
import { RACER_SPEED, TrackOutline } from "@/components/catalog/track-outline";
import { EntityHeader } from "@/components/ui/entity-header";
import { ConstructorLink, DriverLink, Nationality } from "@/components/ui/entity-links";
import { CircuitWinnersTable, MostWinsList } from "@/components/catalog/circuit-tables";
import { getCircuit } from "@/lib/api/queries";
import { formatDate, formatInteger, formatLapTime, formatLength } from "@/lib/format";
import { isSlug } from "@/lib/url";
import { orDash } from "@/components/ui/value";

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
      <h2 id="map-h" className="mb-3 heading text-xl sm:text-[1.375rem]">
        Location
      </h2>
      {/* Not lazy: a lazily loaded frame lets the map measure a container that has no width yet and draw only part of it. */}
      <iframe
        title={`Map of ${name}`}
        src={src}
        referrerPolicy="no-referrer"
        className="h-72 w-full rounded-lg bg-surface-2"
      />
      <p className="mt-2 text-sm text-muted">
        <a
          className="underline underline-offset-4 hover:text-accent"
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
      <div className="mb-12 grid gap-x-12 gap-y-8 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        {c.outline && (
          <figure className="m-0">
            <TrackOutline outline={c.outline} name={c.name} lapMs={c.lap_record_ms} className="mx-auto w-full max-h-[28rem]" />
            {c.outline.marker !== false && c.lap_record_ms != null && (
              <figcaption className="eyebrow mt-3 normal-case tracking-normal">
                The dot runs the lap record ({formatLapTime(c.lap_record_ms)}) at {RACER_SPEED}× speed.
              </figcaption>
            )}
            {c.outline.origin === "geojson" && (
              <figcaption className="eyebrow mt-3 normal-case tracking-normal">
                Current layout. Outline from the f1-circuits data set by Tomislav Bacinger (MIT licence).
              </figcaption>
            )}
          </figure>
        )}
        {!c.outline && (
          <figure className="m-0 flex min-h-56 flex-col items-center justify-center border border-dashed border-line-strong p-6 text-center">
            <p className="display text-5xl text-ghost sm:text-7xl">{c.country}</p>
            <figcaption className="eyebrow mt-3 normal-case tracking-normal">
              No track outline for this circuit. Free map data exists only for the layouts used since 2023 and a few older ones.
            </figcaption>
          </figure>
        )}
        <dl aria-label={`${c.name} facts`} className="self-center border-t border-line">
          <div className="border-b border-line py-4">
            <dt className="label">Lap record</dt>
            <dd className="mt-1">
              {lapRecord ? (
                <>
                  <span className="numeral block text-5xl">{lapRecord}</span>
                  {(c.lap_record_driver || c.lap_record_year) && (
                    <span className="mt-1 block text-muted">
                      {[c.lap_record_driver, c.lap_record_year].filter(Boolean).join(", ")}
                    </span>
                  )}
                </>
              ) : (
                <span className="text-muted">No race lap recorded yet</span>
              )}
            </dd>
          </div>
          <div className="grid grid-cols-2 gap-x-8">
            <div className="border-b border-line py-4">
              <dt className="label">Lap length</dt>
              <dd className="numeral mt-1 text-4xl">
                {c.length_is_estimate && c.length_m ? "≈ " : ""}
                {orDash(formatLength(c.length_m))}
              </dd>
            </div>
            <div className="border-b border-line py-4">
              <dt className="label">Grands Prix</dt>
              <dd className="numeral mt-1 text-4xl">{orDash(formatInteger(c.gp_count))}</dd>
            </div>
          </div>
          <div className="border-b border-line py-4">
            <dt className="label">Last Grand Prix</dt>
            <dd className="mt-1 text-xl font-semibold">{orDash(formatDate(c.last_gp_date))}</dd>
          </div>
        </dl>
      </div>
      {c.lat != null && c.lng != null && <OsmMap lat={c.lat} lng={c.lng} name={c.name} />}
      <section aria-labelledby="records-h" className="mb-10">
        <h2 id="records-h" className="mb-3 heading text-xl sm:text-[1.375rem]">
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
        <h2 id="winners-h" className="mb-3 heading text-xl sm:text-[1.375rem]">
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
