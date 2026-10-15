import type { components } from "@/lib/api/client";
import {
  describePositionChange,
  formatInteger,
  formatLapTime,
  formatPoints,
  formatPosition,
  formatResultTime,
} from "@/lib/format";
import { ConstructorLink, DriverLink } from "@/components/ui/entity-links";
import { DataTable, RowTh, Td, Th, Tr } from "@/components/ui/data-table";
import { Dash, orDash } from "@/components/ui/value";

type S = components["schemas"];

/** Arrow for places gained or lost. Colour is never the only signal: the arrow shape and text say it too. */
export function PositionChange({ change }: { change: number | null }) {
  const d = describePositionChange(change);
  if (!d) return <Dash label="No grid position" />;
  const color = d.direction === "up" ? "text-accent" : d.direction === "down" ? "text-danger" : "text-muted";
  return (
    <span title={d.label} className={`inline-flex items-center justify-end gap-1 ${color}`}>
      <span aria-hidden="true">{d.symbol}</span>
      {d.direction !== "same" && (
        <span aria-hidden="true" className="timing">
          {d.amount}
        </span>
      )}
      <span className="sr-only">{d.label}</span>
    </span>
  );
}

function FastestLapMark() {
  return (
    <span
      title="Fastest lap"
      className="ml-2 inline-block rounded bg-accent-soft px-1 text-xs font-bold text-accent"
    >
      FL<span className="sr-only"> fastest lap</span>
    </span>
  );
}

export function RaceResultsTable({ results, caption }: { results: S["RaceResult"][]; caption: string }) {
  return (
    <DataTable caption={caption} minWidth="52rem">
      <thead>
        <tr>
          <Th align="right">Pos</Th>
          <Th>Driver</Th>
          <Th>Team</Th>
          <Th align="right">Laps</Th>
          <Th align="right">Time / gap</Th>
          <Th>Status</Th>
          <Th align="right">Grid</Th>
          <Th align="right">+/−</Th>
          <Th align="right">Pts</Th>
        </tr>
      </thead>
      <tbody>
        {results.map((r) => (
          <Tr key={r.driver.slug}>
            <Td align="right" className="timing font-bold">
              {orDash(formatPosition(r.position, r.position_text), "Not classified")}
            </Td>
            <RowTh>
              <DriverLink slug={r.driver.slug} name={r.driver.name} />
              {r.fastest_lap === true && <FastestLapMark />}
            </RowTh>
            <Td>
              <ConstructorLink {...r.team} />
            </Td>
            <Td align="right">{orDash(formatInteger(r.laps))}</Td>
            <Td align="right" className="timing whitespace-nowrap">
              {orDash(formatResultTime(r.position, r.time_ms))}
            </Td>
            <Td>{orDash(r.status)}</Td>
            <Td align="right">{orDash(r.grid === 0 ? "Pit lane" : r.grid)}</Td>
            <Td align="right">
              <PositionChange change={r.position_change} />
            </Td>
            <Td align="right" className="font-semibold">
              {orDash(formatPoints(r.points))}
            </Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}

export function QualifyingResultsTable({ results, caption }: { results: S["QualifyingResult"][]; caption: string }) {
  const hasQ2 = results.some((r) => r.q2_ms != null);
  const hasQ3 = results.some((r) => r.q3_ms != null);
  // Older formats had a single timed session: one column instead of Q1 to Q3.
  const single = !hasQ2 && !hasQ3;
  return (
    <DataTable caption={caption} minWidth="38rem">
      <thead>
        <tr>
          <Th align="right">Pos</Th>
          <Th>Driver</Th>
          <Th>Team</Th>
          <Th align="right">{single ? "Time" : "Q1"}</Th>
          {!single && <Th align="right">Q2</Th>}
          {!single && <Th align="right">Q3</Th>}
        </tr>
      </thead>
      <tbody>
        {results.map((r) => (
          <Tr key={r.driver.slug} muted={r.eliminated_in !== null}>
            <Td align="right" className="timing font-bold">
              {orDash(r.position)}
            </Td>
            <RowTh>
              <DriverLink slug={r.driver.slug} name={r.driver.name} />
              {r.eliminated_in && (
                <span title={`Eliminated in ${r.eliminated_in}`} className="ml-2 text-xs font-bold text-muted">
                  out in {r.eliminated_in}
                </span>
              )}
            </RowTh>
            <Td>
              <ConstructorLink {...r.team} />
            </Td>
            <Td align="right" className="timing">
              {orDash(formatLapTime(r.q1_ms))}
            </Td>
            {!single && (
              <Td align="right" className="timing">
                {orDash(formatLapTime(r.q2_ms))}
              </Td>
            )}
            {!single && (
              <Td align="right" className="timing">
                {orDash(formatLapTime(r.q3_ms))}
              </Td>
            )}
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}
