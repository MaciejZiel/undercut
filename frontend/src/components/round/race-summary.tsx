import type { components } from "@/lib/api/client";
import { formatInteger, formatLapTime, formatRaceGap, formatRaceTime } from "@/lib/format";
import Link from "next/link";
import { driverHref } from "@/lib/routes";

type RaceResult = components["schemas"]["RaceResult"];

function Cell({ label, children, note }: { label: string; children: React.ReactNode; note?: React.ReactNode }) {
  return (
    <div className="px-5 py-4 sm:px-6 sm:py-5">
      <dt className="text-xs font-semibold text-muted">{label}</dt>
      <dd className="mt-1.5 text-2xl font-extrabold leading-tight tracking-tight tabular-nums sm:text-[1.75rem]">{children}</dd>
      {note && <dd className="mt-0.5 text-xs text-muted">{note}</dd>}
    </div>
  );
}

/** Four facts about a finished race or sprint, taken from its own classification. Anything missing is left out. */
export function RaceSummary({ results, label }: { results: RaceResult[]; label: string }) {
  const winner = results.find((r) => r.position === 1);
  if (!winner) return null;
  const second = results.find((r) => r.position === 2);
  const margin = second ? formatRaceGap(second, winner) : null;
  const fastest = results.find((r) => r.fastest_lap === true && r.best_lap_ms != null);
  const winnerTime = winner.time_ms != null ? formatRaceTime(winner.time_ms) : null;
  const laps = formatInteger(winner.laps);
  return (
    <dl aria-label={`${label} summary`} className="mb-10 grid grid-cols-2 overflow-hidden rounded-xl bg-surface lg:grid-cols-[1.6fr_1fr_1fr_0.8fr]">
      <div className="col-span-2 bg-accent px-5 py-4 text-accent-fg sm:px-6 sm:py-5 lg:col-span-1">
        <dt className="text-xs font-semibold opacity-80">{label === "Sprint" ? "Sprint winner" : "Race winner"}</dt>
        <dd className="heading mt-1.5 text-3xl">
          <Link href={driverHref(winner.driver.slug)} className="underline-offset-4 hover:underline">
            {winner.driver.name}
          </Link>
        </dd>
        <dd className="mt-1 flex flex-wrap gap-x-4 text-sm opacity-90">
          <span>{winner.team.name}</span>
          {winnerTime && <span className="tabular-nums">{winnerTime}</span>}
        </dd>
      </div>
      {margin && second && (
        <Cell label="Winning margin" note={<>over {second.driver.name}</>}>
          {margin.replace("+", "")}
          <span className="ml-1.5 text-sm font-medium text-muted">{margin.includes(":") ? "" : "sec"}</span>
        </Cell>
      )}
      {fastest && (
        <Cell
          label="Fastest lap"
          note={
            <>
              {fastest.driver.name}, {fastest.team.name}
            </>
          }
        >
          {formatLapTime(fastest.best_lap_ms)}
        </Cell>
      )}
      {laps && (
        <Cell label="Distance" note={`${results.length} drivers started`}>
          {laps}
          <span className="ml-1.5 text-sm font-medium text-muted">laps</span>
        </Cell>
      )}
    </dl>
  );
}
