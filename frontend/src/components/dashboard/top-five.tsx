import Link from "next/link";
import type { components } from "@/lib/api/client";
import type { StandingsKind } from "@/lib/api/queries";
import { formatPoints } from "@/lib/format";
import { ConstructorLink, DriverLink } from "@/components/ui/entity-links";
import { Dash } from "@/components/ui/value";

type TopStandings = components["schemas"]["TopStandings"];

const COPY = {
  drivers: { title: "Drivers", href: "/standings/drivers", noun: "Driver" },
  constructors: { title: "Constructors", href: "/standings/constructors", noun: "Constructor" },
} as const;

const HEX = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

/** A championship top five: position, a team-colour bar beside the name, points and the gap to the leader. */
export function TopFive({ kind, standings }: { kind: StandingsKind; standings: TopStandings }) {
  const copy = COPY[kind];
  const rows = standings.entries.slice(0, 5);
  const leader = Math.max(...rows.map((r) => r.points), 1);
  return (
    <div>
      <p className="flex items-baseline justify-between gap-4 border-b border-line pb-2 text-xs font-semibold text-muted">
        <span>{copy.noun}</span>
        <span>Points</span>
      </p>
      <ol
        aria-label={`${copy.title} championship top five${standings.season ? `, ${standings.season}` : ""}`}
      >
        {rows.map((row) => {
          const behind = leader - row.points;
          const color = row.color && HEX.test(row.color) ? row.color : null;
          return (
            <li key={row.slug} className="grid grid-cols-[1.75rem_minmax(0,1fr)_auto] items-center gap-3 border-b border-line py-3">
              <span className="text-sm font-semibold text-muted">
                <span className="sr-only">Position </span>
                {row.position ?? <Dash />}
              </span>
              <span className="min-w-0 border-l-[3px] pl-3 leading-tight" style={{ borderColor: color ?? "var(--line-strong)" }}>
                <span className="block truncate font-bold">
                  {kind === "drivers" ? (
                    <DriverLink slug={row.slug} name={row.name} />
                  ) : (
                    <ConstructorLink slug={row.slug} name={row.name} dot={false} />
                  )}
                </span>
                {kind === "drivers" && row.team_name && <span className="block truncate text-sm text-muted">{row.team_name}</span>}
              </span>
              <span className="text-right leading-tight">
                <span className="block text-lg font-extrabold tabular-nums">{formatPoints(row.points) ?? <Dash />}</span>
                {behind > 0 && <span className="block text-xs tabular-nums text-muted">−{formatPoints(behind)}</span>}
              </span>
            </li>
          );
        })}
      </ol>
      <Link href={copy.href} className="mt-5 inline-block text-sm font-bold text-accent underline underline-offset-4 hover:no-underline">
        Full table
      </Link>
    </div>
  );
}
