import Link from "next/link";
import type { components } from "@/lib/api/client";
import { formatPoints, formatResultTime } from "@/lib/format";
import { roundHref } from "@/lib/routes";
import { DriverLink } from "@/components/ui/entity-links";
import { Dash } from "@/components/ui/value";

type RaceResult = components["schemas"]["RaceResult"];

const HEX = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

/** Three cards, winner first. Team colour is a top accent border only. */
export function PodiumCards({
  year,
  round,
  name,
  results,
}: {
  year: number;
  round: number;
  name: string;
  results: RaceResult[];
}) {
  const podium = results.filter((r) => r.position !== null && r.position <= 3).sort((a, b) => a.position! - b.position!);
  return (
    <section aria-labelledby="podium-h">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="podium-h" className="text-xl font-extrabold tracking-tight">
          Last race: {name}
        </h2>
        <Link href={roundHref(year, round)} className="text-sm font-semibold text-muted hover:text-accent hover:underline">
          Full results and analysis &rarr;
        </Link>
      </div>
      <ol className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {podium.map((r) => {
          const color = r.team.color && HEX.test(r.team.color) ? r.team.color : "var(--fg-muted)";
          const time = formatResultTime(r.position, r.time_ms);
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
              <p className="timing mt-2 text-sm">{time ?? <Dash />}</p>
              <p className="timing text-sm text-muted">{formatPoints(r.points) ?? "0"} pts</p>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
