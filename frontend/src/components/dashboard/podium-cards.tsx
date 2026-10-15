import Link from "next/link";
import type { components } from "@/lib/api/client";
import { formatDate, formatLapTime } from "@/lib/format";
import { roundHref } from "@/lib/routes";
import { DriverLink } from "@/components/ui/entity-links";
import { ArrowRightIcon } from "@/components/ui/icons";
import { Dash } from "@/components/ui/value";

type S = components["schemas"];

const HEX = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

/** The last race as a short classification: the order is the information, so it is a numbered list. */
export function PodiumCards({
  year,
  round,
  name,
  date,
  podium,
  fastestLap,
}: {
  year: number;
  round: number | null;
  name: string;
  date?: string;
  podium: S["PodiumEntry"][];
  fastestLap: S["FastestLap"] | null;
}) {
  const sorted = [...podium].sort((a, b) => a.position - b.position).slice(0, 3);
  const lap = fastestLap ? formatLapTime(fastestLap.time_ms) : null;
  return (
    <section aria-labelledby="podium-h">
      <p className="text-sm font-bold text-accent">Last race</p>
      <div className="mt-2 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h2 id="podium-h" className="heading text-3xl sm:text-4xl">
          {name}
        </h2>
        {date && <span className="text-sm text-muted">{formatDate(date)}</span>}
      </div>
      <ol className="mt-5 border-t border-line">
        {sorted.map((r) => {
          const color = r.team.color && HEX.test(r.team.color) ? r.team.color : null;
          const first = r.position === 1;
          return (
            <li key={r.driver.slug} className="grid grid-cols-[2.75rem_minmax(0,1fr)] items-center gap-3 border-b border-line py-4">
              <span
                className={`numeral grid size-10 place-items-center rounded-full text-2xl ${first ? "bg-surface text-accent" : "text-muted"}`}
              >
                <span className="sr-only">Position </span>
                {r.position}
              </span>
              <div className="border-l-[3px] pl-3" style={{ borderColor: color ?? "var(--line-strong)" }}>
                <p className={`leading-tight ${first ? "text-lg font-extrabold" : "font-bold"}`}>
                  <DriverLink slug={r.driver.slug} name={r.driver.name} />
                </p>
                <p className="text-sm text-muted">{r.team.name}</p>
              </div>
            </li>
          );
        })}
      </ol>
      <p className="mt-4 flex flex-wrap items-baseline gap-x-3 text-sm text-muted">
        Fastest lap:{" "}
        {fastestLap ? (
          <>
            <span className="rounded-sm bg-accent-soft px-1.5 py-0.5 text-xs font-bold text-accent">Fastest</span>
            <DriverLink slug={fastestLap.driver.slug} name={fastestLap.driver.name} />
            <span className="mono text-fg">{lap ?? <Dash />}</span>
          </>
        ) : (
          <Dash label="Not available" />
        )}
      </p>
      {round != null && (
        <Link
          href={roundHref(year, round)}
          className="t-fast mt-6 inline-flex min-h-11 items-center gap-3 rounded-md bg-accent px-5 py-2.5 text-sm font-bold text-accent-fg hover:bg-accent-hover"
        >
          Full results and analysis
          <ArrowRightIcon />
        </Link>
      )}
    </section>
  );
}
