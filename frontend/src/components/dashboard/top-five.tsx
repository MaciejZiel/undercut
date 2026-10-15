import Link from "next/link";
import type { components } from "@/lib/api/client";
import type { StandingsKind } from "@/lib/api/queries";
import { formatPoints } from "@/lib/format";
import { ConstructorLink, DriverLink } from "@/components/ui/entity-links";
import { Dash } from "@/components/ui/value";

type TopStandings = components["schemas"]["TopStandings"];

const COPY = {
  drivers: { title: "Drivers", href: "/standings/drivers", head: "Driver" },
  constructors: { title: "Constructors", href: "/standings/constructors", head: "Constructor" },
} as const;

/** A championship tower: team colour tick, position, name, points; the bar under a row is the gap to the leader. */
export function TopFive({ kind, standings }: { kind: StandingsKind; standings: TopStandings }) {
  const copy = COPY[kind];
  const rows = standings.entries.slice(0, 5);
  const leader = Math.max(...rows.map((r) => r.points), 1);
  const id = `top-${kind}-h`;
  return (
    <section aria-labelledby={id}>
      <div className="mb-3 flex items-baseline justify-between gap-2">
        <h2 id={id} className="text-2xl font-bold tracking-tight">
          {copy.title} top 5
        </h2>
        <Link href={copy.href} className="text-sm font-semibold text-muted hover:text-fg">
          Full table &rarr;
        </Link>
      </div>
      <ol
        aria-label={`${copy.title} championship top five${standings.season ? `, ${standings.season}` : ""}`}
        className="border-t-2 border-fg"
      >
        {rows.map((row) => {
          const behind = leader - row.points;
          return (
            <li
              key={row.slug}
              className="relative grid grid-cols-[2.25rem_0.375rem_minmax(0,1fr)_auto] items-center gap-3 border-b border-line py-3"
            >
              <span className="numeral text-[1.625rem]">
                <span className="sr-only">Position </span>
                {row.position ?? <Dash />}
              </span>
              <span
                aria-hidden="true"
                className="h-7 w-1.5 rounded-[1px]"
                style={{ backgroundColor: row.color ?? "var(--line)" }}
              />
              <span className="min-w-0 leading-tight">
                <span className="block truncate font-semibold">
                  {kind === "drivers" ? (
                    <DriverLink slug={row.slug} name={row.name} />
                  ) : (
                    <ConstructorLink slug={row.slug} name={row.name} dot={false} />
                  )}
                </span>
                {kind === "drivers" && row.team_name && <span className="block truncate text-sm text-muted">{row.team_name}</span>}
              </span>
              <span className="text-right leading-tight">
                <span className="mono block text-base font-medium">{formatPoints(row.points) ?? <Dash />}</span>
                {behind > 0 && <span className="mono block text-xs text-muted">−{formatPoints(behind)}</span>}
              </span>
              <span
                aria-hidden="true"
                className="absolute bottom-[-1px] left-0 h-[3px]"
                style={{ width: `${Math.round((row.points / leader) * 100)}%`, backgroundColor: row.color ?? "var(--fg)" }}
              />
            </li>
          );
        })}
      </ol>
    </section>
  );
}
