import Link from "next/link";
import type { components } from "@/lib/api/client";
import { formatLapTime } from "@/lib/format";
import { roundHref } from "@/lib/routes";
import { DriverLink } from "@/components/ui/entity-links";
import { Dash } from "@/components/ui/value";

type S = components["schemas"];

const HEX = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

/** Three cards, winner first. Team colour is a top accent border only. */
export function PodiumCards({
  year,
  round,
  name,
  podium,
  fastestLap,
}: {
  year: number;
  round: number | null;
  name: string;
  podium: S["PodiumEntry"][];
  fastestLap: S["FastestLap"] | null;
}) {
  const sorted = [...podium].sort((a, b) => a.position - b.position).slice(0, 3);
  const lap = fastestLap ? formatLapTime(fastestLap.time_ms) : null;
  return (
    <section aria-labelledby="podium-h">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="podium-h" className="text-xl font-extrabold tracking-tight">
          Last race: {name}
        </h2>
        {round != null && (
          <Link href={roundHref(year, round)} className="text-sm font-semibold text-muted hover:text-accent hover:underline">
            Full results and analysis &rarr;
          </Link>
        )}
      </div>
      <ol className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {sorted.map((r) => {
          const color = r.team.color && HEX.test(r.team.color) ? r.team.color : "var(--fg-muted)";
          return (
            <li
              key={r.driver.slug}
              className="rounded-lg border border-line border-t-4 bg-surface p-4"
              style={{ borderTopColor: color }}
            >
              <p className="timing text-3xl font-extrabold">
                <span className="sr-only">Position </span>
                {r.position}
              </p>
              <p className="mt-1 text-lg">
                <DriverLink slug={r.driver.slug} name={r.driver.name} />
              </p>
              <p className="text-sm text-muted">{r.team.name}</p>
            </li>
          );
        })}
      </ol>
      <p className="mt-3 text-sm text-muted">
        Fastest lap:{" "}
        {fastestLap ? (
          <>
            <DriverLink slug={fastestLap.driver.slug} name={fastestLap.driver.name} />{" "}
            <span className="timing">{lap ?? <Dash />}</span>
          </>
        ) : (
          <Dash label="Not available" />
        )}
      </p>
    </section>
  );
}
