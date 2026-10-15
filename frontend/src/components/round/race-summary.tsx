import Link from "next/link";
import type { components } from "@/lib/api/client";
import { formatInteger, formatLapTime, formatRaceGap, formatRaceTime } from "@/lib/format";
import { driverHref } from "@/lib/routes";

type RaceResult = components["schemas"]["RaceResult"];

const HEX = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

/**
 * The result in one sentence, built only from numbers that are in the table below it. The team colour
 * bar on the left is the same mark as in the tables. Anything missing is left out, never guessed.
 */
export function RaceSummary({ results, label }: { results: RaceResult[]; label: string }) {
  const winner = results.find((r) => r.position === 1);
  if (!winner) return null;
  const second = results.find((r) => r.position === 2);
  const margin = second ? formatRaceGap(second, winner) : null;
  const fastest = results.find((r) => r.fastest_lap === true && r.best_lap_ms != null);
  const winnerTime = winner.time_ms != null ? formatRaceTime(winner.time_ms) : null;
  const laps = formatInteger(winner.laps);
  const color = winner.team.color && HEX.test(winner.team.color) ? winner.team.color : null;
  const sprint = label === "Sprint";
  return (
    <section
      aria-label={`${label} summary`}
      className="mb-10 border-l-[6px] pl-5"
      style={{ borderColor: color ?? "var(--line-strong)" }}
    >
      <p className="max-w-3xl text-xl font-semibold leading-snug sm:text-[1.375rem]">
        <Link href={driverHref(winner.driver.slug)} className="font-extrabold underline-offset-4 hover:text-accent hover:underline">
          {winner.driver.name}
        </Link>{" "}
        {sprint ? "wins the sprint" : "wins"} for {winner.team.name}
        {winnerTime && (
          <>
            {" "}
            in <span className="tabular-nums">{winnerTime}</span>
          </>
        )}
        {margin && second && (
          <>
            , <span className="tabular-nums">{margin.replace("+", "")}</span>
            {margin.includes(":") ? "" : " s"} ahead of {second.driver.name}
          </>
        )}
        .
      </p>
      <p className="mt-2 text-sm text-muted">
        {fastest && (
          <>
            Fastest lap {fastest.driver.name}, <span className="tabular-nums">{formatLapTime(fastest.best_lap_ms)}</span>.{" "}
          </>
        )}
        {laps && <span className="tabular-nums">{laps} laps</span>}
        {laps && results.length > 0 ? `, ${results.length} drivers.` : ""}
      </p>
    </section>
  );
}
