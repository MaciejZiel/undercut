import Link from "next/link";
import type { StandingsKind, Standings } from "@/lib/api/queries";
import { formatPoints } from "@/lib/format";
import { ConstructorLink, DriverLink } from "@/components/ui/entity-links";
import { DataTable, RowTh, Td, Th, Tr } from "@/components/ui/data-table";
import { Dash } from "@/components/ui/value";

const COPY = {
  drivers: { title: "Drivers", href: "/standings/drivers", head: "Driver" },
  constructors: { title: "Constructors", href: "/standings/constructors", head: "Constructor" },
} as const;

export function TopFive({ kind, standings }: { kind: StandingsKind; standings: Standings }) {
  const copy = COPY[kind];
  const rows = standings.results.slice(0, 5);
  const id = `top-${kind}-h`;
  return (
    <section aria-labelledby={id}>
      <div className="mb-3 flex items-baseline justify-between gap-2">
        <h2 id={id} className="text-xl font-extrabold tracking-tight">
          {copy.title} top 5
        </h2>
        <Link href={copy.href} className="text-sm font-semibold text-muted hover:text-accent hover:underline">
          Full table &rarr;
        </Link>
      </div>
      <DataTable
        caption={`${copy.title} championship top five${standings.season ? `, ${standings.season}` : ""}`}
        minWidth="0"
      >
        <thead>
          <tr>
            <Th className="w-12">Pos</Th>
            <Th>{copy.head}</Th>
            <Th align="right">Points</Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <Tr key={row.entity.id}>
              <RowTh className="timing font-bold">{row.position ?? <Dash />}</RowTh>
              <Td>
                {kind === "drivers" ? (
                  <DriverLink slug={row.entity.slug} name={row.entity.name} />
                ) : (
                  <ConstructorLink slug={row.entity.slug} name={row.entity.name} />
                )}
              </Td>
              <Td align="right" className="timing font-bold">
                {formatPoints(row.points) ?? <Dash />}
              </Td>
            </Tr>
          ))}
        </tbody>
      </DataTable>
    </section>
  );
}
