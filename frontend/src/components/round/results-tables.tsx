import { Fragment } from "react";
import type { components } from "@/lib/api/client";
import {
  describePositionChange,
  formatGap,
  formatInteger,
  formatLapTime,
  formatPoints,
  formatPosition,
  formatRaceGap,
} from "@/lib/format";
import { ConstructorLink, DriverLink } from "@/components/ui/entity-links";
import { DataTable, RowTh, Td, Th, Tr } from "@/components/ui/data-table";
import { Dash, orDash } from "@/components/ui/value";

type S = components["schemas"];

/** Arrow for places gained or lost. Colour is never the only signal: the arrow shape and text say it too. */
export function PositionChange({ change }: { change: number | null }) {
  const d = describePositionChange(change);
  if (!d) return <Dash label="No grid position" />;
  const color = d.direction === "up" ? "text-positive" : d.direction === "down" ? "text-danger" : "text-muted";
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

const FINISHED = new Set(["Finished", "Lapped"]);

/** Milliseconds behind the winner for a car that finished on the winner's lap, otherwise null. */
function leadLapGap(r: S["RaceResult"], winner: S["RaceResult"] | undefined): number | null {
  if (!winner || r.position === 1 || r.time_ms == null || winner.time_ms == null) return null;
  if (r.laps == null || winner.laps == null || r.laps !== winner.laps) return null;
  if (r.status !== "Finished") return null;
  return r.time_ms > winner.time_ms ? r.time_ms - winner.time_ms : null;
}

/** The gap column: the winner's time, the gap with a bar drawn to scale, laps down, or why the car stopped. */
function GapCell({ r, winner, maxGap }: { r: S["RaceResult"]; winner: S["RaceResult"] | undefined; maxGap: number }) {
  const text = formatRaceGap(r, winner);
  const gap = leadLapGap(r, winner);
  if (r.position === 1 && text) return <span>{text}</span>;
  if (text && gap != null) {
    return (
      <span className="inline-flex w-36 flex-col items-end max-sm:w-24">
        <span>{text}</span>
        <span
          aria-hidden="true"
          className="mt-1 block h-[3px] rounded-[1px] bg-accent/40"
          style={{ width: `${Math.max(2, Math.round((gap / maxGap) * 100))}%`, minWidth: "2px" }}
        />
      </span>
    );
  }
  if (text) return <span>{text}</span>;
  if (r.status && !FINISHED.has(r.status)) {
    return (
      <span className="text-muted">
        {r.status}
        {r.laps != null ? `, lap ${r.laps}` : ""}
      </span>
    );
  }
  return <Dash label="No data" />;
}

export function RaceResultsTable({ results, caption }: { results: S["RaceResult"][]; caption: string }) {
  const winner = results.find((r) => r.position === 1);
  const gaps = results.map((r) => leadLapGap(r, winner)).filter((g): g is number => g != null);
  const maxGap = Math.max(1, ...gaps);
  return (
    <DataTable caption={caption} minWidth="46rem" stack>
      <thead>
        <tr>
          <Th align="right">Pos</Th>
          <Th>Driver</Th>
          <Th>Team</Th>
          <Th align="right">Gap</Th>
          <Th align="right">Grid</Th>
          <Th align="right">+/−</Th>
          <Th align="right">Pts</Th>
        </tr>
      </thead>
      <tbody>
        {results.map((r) => (
          <Tr key={r.driver.slug}>
            <Td align="right" className="c-pos timing font-bold">
              {orDash(formatPosition(r.position, r.position_text), "Not classified")}
            </Td>
            <RowTh color={r.team.color} className="c-name">
              <DriverLink slug={r.driver.slug} name={r.driver.name} />
              {r.fastest_lap === true && <FastestLapMark />}
            </RowTh>
            <Td className="c-sub">
              <ConstructorLink {...r.team} dot={false} />
              {r.grid != null && r.grid > 0 && <span className="sm:hidden"> · from P{r.grid}</span>}
            </Td>
            <Td align="right" className="c-gap timing whitespace-nowrap">
              <GapCell r={r} winner={winner} maxGap={maxGap} />
            </Td>
            <Td align="right" className="c-hide">
              {orDash(r.grid === 0 ? "Pit lane" : r.grid)}
            </Td>
            <Td align="right" className="c-hide">
              <PositionChange change={r.position_change} />
            </Td>
            <Td align="right" className="c-end font-semibold">
              {orDash(formatPoints(r.points))}
              {r.points != null && r.points > 0 && <span className="font-normal sm:hidden"> pts</span>}
            </Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}

export function QualifyingResultsTable({
  results,
  caption,
  prefix = "Q",
}: {
  results: S["QualifyingResult"][];
  caption: string;
  /** "SQ" for sprint qualifying, whose parts are SQ1 to SQ3. */
  prefix?: "Q" | "SQ";
}) {
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
          <Th align="right">{single ? "Time" : `${prefix}1`}</Th>
          {!single && <Th align="right">{prefix}2</Th>}
          {!single && <Th align="right">{prefix}3</Th>}
        </tr>
      </thead>
      <tbody>
        {results.map((r, i) => {
          const next = results[i + 1];
          // A cut falls where the session in which the next car was knocked out differs from this car's.
          const cutDigit = next && next.eliminated_in !== r.eliminated_in ? next.eliminated_in?.match(/(\d)$/)?.[1] : undefined;
          return (
            <Fragment key={r.driver.slug}>
              <Tr muted={r.eliminated_in !== null}>
                <Td align="right" className="timing font-bold">
                  {orDash(r.position)}
                </Td>
                <RowTh color={r.team.color}>
                  <DriverLink slug={r.driver.slug} name={r.driver.name} />
                  {r.eliminated_in && (
                    <span title={`Eliminated in ${r.eliminated_in}`} className="ml-2 text-xs font-bold text-muted">
                      out in {r.eliminated_in}
                    </span>
                  )}
                </RowTh>
                <Td>
                  <ConstructorLink {...r.team} dot={false} />
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
                  <Td align="right" className={`timing ${r.position === 1 ? "font-extrabold" : ""}`}>
                    {orDash(formatLapTime(r.q3_ms))}
                  </Td>
                )}
              </Tr>
              {cutDigit && (
                <tr aria-hidden="true">
                  <td colSpan={single ? 4 : 6} className="border-b-[3px] border-fg p-0 pb-0.5 text-right text-xs font-bold text-muted">
                    {prefix}
                    {Number(cutDigit) + 1} cut
                  </td>
                </tr>
              )}
            </Fragment>
          );
        })}
      </tbody>
    </DataTable>
  );
}


/** Practice classification: best lap, the gap to the fastest car and the laps driven. */
export function PracticeResultsTable({ results, caption }: { results: S["PracticeResult"][]; caption: string }) {
  return (
    <DataTable caption={caption} minWidth="36rem">
      <thead>
        <tr>
          <Th align="right">Pos</Th>
          <Th>Driver</Th>
          <Th>Team</Th>
          <Th align="right">Best lap</Th>
          <Th align="right">Gap</Th>
          <Th align="right">Laps</Th>
        </tr>
      </thead>
      <tbody>
        {results.map((r) => (
          <Tr key={r.driver.slug} muted={r.best_lap_ms === null}>
            <Td align="right" className="timing font-bold">
              {orDash(r.position, "No time set")}
            </Td>
            <RowTh color={r.team.color}>
              <DriverLink slug={r.driver.slug} name={r.driver.name} />
            </RowTh>
            <Td>
              <ConstructorLink {...r.team} dot={false} />
            </Td>
            <Td align="right" className="mono">
              {orDash(formatLapTime(r.best_lap_ms), "No time set")}
            </Td>
            <Td align="right" className="mono text-muted">
              {r.position === 1 ? <Dash label="Fastest" /> : orDash(formatGap(r.gap_ms))}
            </Td>
            <Td align="right">{orDash(formatInteger(r.laps))}</Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}
