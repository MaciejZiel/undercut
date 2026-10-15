import Link from "next/link";
import type { components } from "@/lib/api/client";
import { formatInteger, formatLapTime, formatPoints, formatRaceTime } from "@/lib/format";
import { roundHref } from "@/lib/routes";
import { DriverLink } from "@/components/ui/entity-links";
import { Dash } from "@/components/ui/value";

type S = components["schemas"];

const HEX = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;
const stagger = (i: number) => ({ "--i": i }) as React.CSSProperties;

/** The last race as a short classification: the winner large, the rest as lines. Time, laps and points come from the results when they are there. */
export function PodiumCards({
  year,
  round,
  name,
  podium,
  fastestLap,
  results = null,
}: {
  year: number;
  round: number | null;
  name: string;
  date?: string;
  podium: S["PodiumEntry"][];
  fastestLap: S["FastestLap"] | null;
  results?: S["RaceResult"][] | null;
}) {
  const sorted = [...podium].sort((a, b) => a.position - b.position).slice(0, 3);
  const lap = fastestLap ? formatLapTime(fastestLap.time_ms) : null;
  const resultOf = (slug: string) => results?.find((r) => r.driver.slug === slug);
  const place = name.replace(/ Grand Prix.*$/, "");
  return (
    <section aria-labelledby="podium-h">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow mb-1.5">
            Last classified{round != null ? ` / Round ${round}` : ""}
          </p>
          <h2 id="podium-h" className="heading text-[1.5rem] sm:text-[1.625rem]">
            {place}. Settled.
          </h2>
          <p className="sr-only">{name}</p>
        </div>
        {round != null && (
          <Link href={roundHref(year, round)} className="eyebrow whitespace-nowrap hover:text-accent">
            Race report ↗
          </Link>
        )}
      </div>
      <ol>
        {sorted.map((r, index) => {
          const color = r.team.color && HEX.test(r.team.color) ? r.team.color : null;
          const first = r.position === 1;
          const res = resultOf(r.driver.slug);
          const points = res?.points != null ? formatPoints(res.points) : null;
          const time = first && res?.time_ms != null ? formatRaceTime(res.time_ms) : null;
          const laps = first && res?.laps != null ? formatInteger(res.laps) : null;
          return (
            <li
              key={r.driver.slug}
              style={stagger(index + 2)}
              className={`rise grid items-center gap-x-3 border-b ${first ? "grid-cols-[3.5rem_minmax(0,1fr)] border-fg py-4 sm:grid-cols-[4.5rem_minmax(0,1fr)_auto]" : "grid-cols-[2.5rem_minmax(0,1fr)_auto] border-line py-3"}`}
            >
              <span className={first ? "numeral text-[2.75rem] tracking-[-0.06em] sm:text-[3.5rem]" : "eyebrow"}>
                <span className="sr-only">Position </span>
                {String(r.position).padStart(2, "0")}
              </span>
              <div className={first ? "" : "border-l-[3px] pl-2.5"} style={first ? undefined : { borderColor: color ?? "var(--line-strong)" }}>
                <p className={`leading-tight ${first ? "text-[1.5rem] tracking-[-0.035em] [&_a]:font-black" : "text-base [&_a]:font-bold"}`}>
                  <DriverLink slug={r.driver.slug} name={r.driver.name} stretch />
                </p>
                {first ? (
                  <p className="eyebrow mt-1.5 flex items-center normal-case tracking-normal">
                    <span aria-hidden="true" className="mr-2 inline-block h-[3px] w-4" style={{ backgroundColor: color ?? "var(--line-strong)" }} />
                    {r.team.name}
                  </p>
                ) : null}
              </div>
              <p className={`text-[0.8125rem] leading-relaxed ${first ? "col-start-2 mt-2 sm:col-start-auto sm:mt-0 sm:text-right" : "text-right"}`}>
                {time && <b className="block tabular-nums">{time}</b>}
                <span className="eyebrow">
                  {[first ? null : r.team.name, laps ? `${laps} laps` : null, points ? `${points} pts` : null].filter(Boolean).join(" / ")}
                </span>
              </p>
            </li>
          );
        })}
      </ol>
      <p className="mt-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-[0.8125rem] text-muted">
        <span className="flex flex-wrap items-baseline gap-x-3">
          Fastest lap:{" "}
          {fastestLap ? (
            <>
              <DriverLink slug={fastestLap.driver.slug} name={fastestLap.driver.name} />
              <span className="mono text-fg">{lap ?? <Dash />}</span>
            </>
          ) : (
            <Dash label="Not available" />
          )}
        </span>
        {round != null && (
          <Link href={roundHref(year, round)} className="font-bold text-fg underline decoration-accent decoration-2 underline-offset-4 hover:text-accent">
            Full results and analysis ↗
          </Link>
        )}
      </p>
    </section>
  );
}
