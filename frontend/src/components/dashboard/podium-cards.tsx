import Link from "next/link";
import type { components } from "@/lib/api/client";
import { formatLapTime } from "@/lib/format";
import { roundHref } from "@/lib/routes";
import { DriverLink } from "@/components/ui/entity-links";
import { Dash } from "@/components/ui/value";

type S = components["schemas"];

const HEX = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

function Swatch({ color }: { color: string | null | undefined }) {
  const valid = color && HEX.test(color) ? color : null;
  return (
    <span
      aria-hidden="true"
      className="inline-block size-3.5 shrink-0 rounded-[1px]"
      style={{ backgroundColor: valid ?? "var(--fg-muted)", opacity: valid ? 1 : 0.5 }}
    />
  );
}

/** Winner large, the other two beside it as plain rows (a podium is not three equal boxes). */
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
  const [winner, ...others] = sorted;
  const lap = fastestLap ? formatLapTime(fastestLap.time_ms) : null;
  return (
    <section aria-labelledby="podium-h">
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="podium-h" className="text-2xl font-bold tracking-tight">
          Last race: {name}
        </h2>
        {round != null && (
          <Link href={roundHref(year, round)} className="text-sm font-semibold text-muted hover:text-fg">
            Full results and analysis &rarr;
          </Link>
        )}
      </div>
      <ol className="grid grid-cols-1 border-t-2 border-fg md:grid-cols-[minmax(0,6fr)_minmax(0,5fr)] md:grid-rows-2">
        <li className="border-b border-line py-6 md:row-span-2 md:border-b-0 md:border-r md:pr-8">
          <p className="numeral text-[7rem] leading-[0.8] sm:text-[9rem]">
            <span className="sr-only">Position </span>
            {winner?.position}
          </p>
          {winner && (
            <>
              <p className="mt-4 text-3xl font-bold leading-tight tracking-tight">
                <DriverLink slug={winner.driver.slug} name={winner.driver.name} />
              </p>
              <p className="mt-1 inline-flex items-center gap-2 text-muted">
                <Swatch color={winner.team.color} />
                {winner.team.name}
              </p>
            </>
          )}
        </li>
        {others.map((r, i) => (
          <li
            key={r.driver.slug}
            className={`grid grid-cols-[3.5rem_1fr] items-center gap-4 border-b border-line py-5 md:col-start-2 md:pl-8 ${
              i === 0 ? "md:row-start-1" : "md:row-start-2 md:border-b-0"
            }`}
          >
            <p className="numeral text-6xl">
              <span className="sr-only">Position </span>
              {r.position}
            </p>
            <div>
              <p className="text-xl font-bold leading-tight">
                <DriverLink slug={r.driver.slug} name={r.driver.name} />
              </p>
              <p className="mt-0.5 inline-flex items-center gap-2 text-sm text-muted">
                <Swatch color={r.team.color} />
                {r.team.name}
              </p>
            </div>
          </li>
        ))}
      </ol>
      <p className="mt-4 flex flex-wrap items-baseline gap-x-3 text-[0.9375rem] text-muted">
        Fastest lap:{" "}
        {fastestLap ? (
          <>
            <span className="rounded-sm bg-fg px-1.5 py-0.5 text-[0.6875rem] font-bold uppercase tracking-wider text-bg">Fastest</span>
            <DriverLink slug={fastestLap.driver.slug} name={fastestLap.driver.name} />
            <span className="mono text-fg">{lap ?? <Dash />}</span>
          </>
        ) : (
          <Dash label="Not available" />
        )}
      </p>
    </section>
  );
}
