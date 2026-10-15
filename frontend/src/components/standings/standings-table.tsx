import type { StandingRow, StandingsKind } from "@/lib/api/queries";
import { formatInteger, formatPoints } from "@/lib/format";
import { ConstructorLink, DriverLink } from "@/components/ui/entity-links";
import { DataTable, RowTh, Td, Th, Tr } from "@/components/ui/data-table";
import { Dash } from "@/components/ui/value";

/** Position cell: the number, or the position text (for example "-") when the API has no number. */
function PositionCell({ row }: { row: StandingRow }) {
  const text = row.position ?? (row.position_text && row.position_text !== "-" ? row.position_text : null);
  return text === null ? <Dash label="Not classified" /> : <span className="font-bold">{text}</span>;
}

/** The leader has no gap; everyone else trails by a positive amount. */
export function GapCell({ row }: { row: StandingRow }) {
  if (row.position === 1) return <Dash label="Championship leader" />;
  const gap = formatPoints(Math.abs(row.gap_to_leader));
  return gap === null ? <Dash /> : <span>-{gap}</span>;
}

export function StandingsTable({
  kind,
  rows,
  caption,
}: {
  kind: StandingsKind;
  rows: StandingRow[];
  caption: string;
}) {
  return (
    <DataTable caption={caption} minWidth="36rem">
      <thead>
        <tr>
          <Th className="w-14">Pos</Th>
          <Th>{kind === "drivers" ? "Driver" : "Constructor"}</Th>
          <Th align="right">Points</Th>
          <Th align="right">Wins</Th>
          <Th align="right">Podiums</Th>
          <Th align="right">Gap</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <Tr key={row.entity.id}>
            <RowTh className="timing">
              <PositionCell row={row} />
            </RowTh>
            <Td>
              {kind === "drivers" ? (
                <span className="inline-flex flex-wrap items-baseline gap-x-2">
                  <DriverLink slug={row.entity.slug} name={row.entity.name} />
                  {row.entity.code && <span className="text-xs font-bold text-muted">{row.entity.code}</span>}
                </span>
              ) : (
                <ConstructorLink slug={row.entity.slug} name={row.entity.name} />
              )}
            </Td>
            <Td align="right" className="timing font-bold">
              {formatPoints(row.points) ?? <Dash />}
            </Td>
            <Td align="right" className="timing">
              {formatInteger(row.wins) ?? <Dash />}
            </Td>
            <Td align="right" className="timing">
              {formatInteger(row.podiums) ?? <Dash />}
            </Td>
            <Td align="right" className="timing">
              <GapCell row={row} />
            </Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}
