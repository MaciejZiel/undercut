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
const stagger = (i: number) => ({ "--i": i }) as React.CSSProperties;

/** A championship top five: position, a team-colour bar beside the name, points and the gap to the leader. */
export function TopFive({ kind, standings }: { kind: StandingsKind; standings: TopStandings }) {
  const copy = COPY[kind];
  const rows = standings.entries.slice(0, 5);
  const leader = Math.max(...rows.map((r) => r.points), 1);
  return (
    <div>
      <p className="eyebrow grid grid-cols-[2.25rem_1fr_auto] border-b border-fg pb-2">
        <span>Pos</span>
        <span>{copy.noun}</span>
        <span>Pts</span>
      </p>
      <ol aria-label={`${copy.title} championship top five${standings.season ? `, ${standings.season}` : ""}`}>
        {rows.map((row, index) => {
          const behind = leader - row.points;
          const color = row.color && HEX.test(row.color) ? row.color : null;
          return (
            <li
              key={row.slug}
              style={stagger(index + 3)}
              className="rise grid min-h-[2.75rem] grid-cols-[2.25rem_minmax(0,1fr)_auto] items-center border-b border-line py-2"
            >
              <span className="eyebrow">
                <span className="sr-only">Position </span>
                {row.position != null ? String(row.position).padStart(2, "0") : <Dash />}
              </span>
              <span className="min-w-0 border-l-[3px] pl-2.5 leading-tight" style={{ borderColor: color ?? "var(--line-strong)" }}>
                <span className="block truncate text-[0.8125rem] font-bold">
                  {kind === "drivers" ? (
                    <DriverLink slug={row.slug} name={row.name} stretch />
                  ) : (
                    <ConstructorLink slug={row.slug} name={row.name} dot={false} stretch />
                  )}
                </span>
                {kind === "drivers" && row.team_name && <span className="mt-0.5 block truncate text-xs text-muted">{row.team_name}</span>}
              </span>
              <span className="text-right leading-tight">
                <span className="block text-[1.1875rem] font-extrabold tabular-nums tracking-[-0.03em]">{formatPoints(row.points) ?? <Dash />}</span>
                {behind > 0 && <span className="block text-xs tabular-nums text-muted">−{formatPoints(behind)}</span>}
              </span>
            </li>
          );
        })}
      </ol>
      <Link href={copy.href} className="eyebrow mt-4 inline-block whitespace-nowrap hover:text-accent">
        Full table →
      </Link>
    </div>
  );
}
