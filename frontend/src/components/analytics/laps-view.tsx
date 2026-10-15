"use client";

import { useMemo, useState } from "react";
import { readChartTokens, type ChartTokens } from "@/components/charts/tokens";
import { DataTable, RowTh, Td, Th, Tr } from "@/components/ui/data-table";
import { Dash, orDash } from "@/components/ui/value";
import { formatLapTime } from "@/lib/format";
import {
  bestOf,
  defaultLapDrivers,
  fetchLaps,
  fetchPositions,
  formatSeconds,
  lapMatrix,
  teamColor,
  type AnalyticsRef,
  type Laps,
  type Positions,
} from "./data";
import { AnalyticsChart, ChartFrame, RequestState } from "./chart-frame";
import { useAnalytics } from "./hooks";
import { buildLapsOption } from "./options";

const chip = "t-fast inline-flex items-center gap-2 rounded-sm border px-2.5 py-1 text-sm font-semibold";

export function LapsView({ refs }: { refs: AnalyticsRef }) {
  // The driver list (and who finished on top) comes from the positions request, shared with the Positions view.
  const positions = useAnalytics("positions", refs, () => fetchPositions(refs));
  return (
    <RequestState
      query={positions}
      isEmpty={(d) => d.drivers.length === 0}
      emptyTitle="No lap times"
      emptyDescription="Lap times appear here once lap data has been processed."
    >
      {(p) => <LapsPanel key={`${refs.session}`} refs={refs} positions={p} />}
    </RequestState>
  );
}

function LapsPanel({ refs, positions }: { refs: AnalyticsRef; positions: Positions }) {
  const [selected, setSelected] = useState<string[]>(() => defaultLapDrivers(positions));
  const [hideSlow, setHideSlow] = useState(true);
  const codes = useMemo(() => positions.drivers.map((d) => d.code).filter((c) => selected.includes(c)), [positions, selected]);
  const neutral = readChartTokens().muted;

  const toggle = (code: string) =>
    setSelected((cur) => (cur.includes(code) ? cur.filter((c) => c !== code) : [...cur, code]));

  return (
    <div className="space-y-4">
      <fieldset>
        <legend className="mb-2 text-xs font-bold text-muted">
          Drivers ({codes.length} of {positions.drivers.length})
        </legend>
        <ul className="flex flex-wrap gap-1.5">
          {positions.drivers.map((d) => {
            const on = codes.includes(d.code);
            return (
              <li key={d.code}>
                <button
                  type="button"
                  aria-pressed={on}
                  title={d.full_name}
                  onClick={() => toggle(d.code)}
                  className={`${chip} ${on ? "border-line bg-surface text-fg" : "border-transparent bg-surface-2 text-muted"}`}
                >
                  <span
                    aria-hidden="true"
                    className="inline-block h-3.5 w-[3px]"
                    style={{ backgroundColor: teamColor(d.color_hex, neutral), opacity: on ? 1 : 0.4 }}
                  />
                  {d.code}
                </button>
              </li>
            );
          })}
        </ul>
      </fieldset>
      <label className="inline-flex items-center gap-2 text-sm font-semibold">
        <input type="checkbox" checked={hideSlow} onChange={(e) => setHideSlow(e.target.checked)} className="size-4 accent-[var(--accent)]" />
        Hide in/out and safety-car laps
      </label>
      {codes.length === 0 ? (
        <p className="rounded-sm border border-dashed border-line p-6 text-center text-muted">Pick at least one driver to draw the chart.</p>
      ) : (
        <LapsData refs={refs} codes={codes} hideSlow={hideSlow} />
      )}
    </div>
  );
}

function LapsData({ refs, codes, hideSlow }: { refs: AnalyticsRef; codes: string[]; hideSlow: boolean }) {
  const key = codes.join(",");
  const query = useAnalytics("laps", refs, () => fetchLaps(refs, codes, hideSlow), key, hideSlow);
  return (
    <RequestState
      query={query}
      isEmpty={(d) => d.drivers.every((x) => x.lap_numbers.length === 0)}
      emptyTitle="No laps to show"
      emptyDescription="Try showing the in/out and safety-car laps as well."
    >
      {(data) => <LapsOutput data={data} />}
    </RequestState>
  );
}

function LapsOutput({ data }: { data: Laps }) {
  const option = useMemo(() => (t: ChartTokens) => buildLapsOption(data, t), [data]);
  const title = `${data.session.year} ${data.session.round_name}: lap times`;
  const neutral = readChartTokens().muted;
  const legend = (
    <ul aria-label="Drivers" className="flex flex-wrap gap-2 lg:flex-col">
      {data.drivers.map((d) => (
        <li key={d.code} className="inline-flex items-center gap-2 text-sm font-semibold">
          <span aria-hidden="true" className="inline-block h-3.5 w-[3px]" style={{ backgroundColor: teamColor(d.color_hex, neutral) }} />
          {d.code}
        </li>
      ))}
    </ul>
  );
  return (
    <div className="space-y-4">
      <ChartFrame
        title={title}
        legend={legend}
        chart={<AnalyticsChart option={option} label={`${title}. A table is available.`} />}
        table={<LapMatrixTable data={data} />}
      />
      <LapSummaryTable data={data} />
    </div>
  );
}

export function LapMatrixTable({ data }: { data: Laps }) {
  const rows = lapMatrix(data);
  return (
    <div className="max-h-[32rem] overflow-auto rounded-sm">
      <DataTable caption="Lap times by lap" minWidth="20rem">
        <thead>
          <tr>
            <Th align="right">Lap</Th>
            {data.drivers.map((d) => (
              <Th key={d.code} align="right">
                {d.code}
              </Th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <Tr key={r.lap}>
              <RowTh className="timing text-right font-bold">{r.lap}</RowTh>
              {r.times.map((ms, i) => (
                <Td key={i} align="right" className="timing">
                  {orDash(formatLapTime(ms), "No lap time")}
                </Td>
              ))}
            </Tr>
          ))}
        </tbody>
      </DataTable>
    </div>
  );
}

export function LapSummaryTable({ data }: { data: Laps }) {
  return (
    <DataTable caption="Lap time summary and best sector times" minWidth="44rem">
      <thead>
        <tr>
          <Th>Driver</Th>
          <Th align="right">Laps</Th>
          <Th align="right">Best</Th>
          <Th align="right">Median</Th>
          <Th align="right">Std dev</Th>
          <Th align="right">Best S1</Th>
          <Th align="right">Best S2</Th>
          <Th align="right">Best S3</Th>
        </tr>
      </thead>
      <tbody>
        {data.drivers.map((d) => (
          <Tr key={d.code}>
            <RowTh className="font-semibold">
              {d.code} <span className="font-normal text-muted">{d.constructor_name}</span>
            </RowTh>
            <Td align="right" className="timing">{d.summary.count}</Td>
            <Td align="right" className="timing">{orDash(formatLapTime(d.summary.best_ms))}</Td>
            <Td align="right" className="timing">{orDash(formatLapTime(d.summary.median_ms == null ? null : Math.round(d.summary.median_ms)))}</Td>
            <Td align="right" className="timing">{orDash(formatSeconds(d.summary.stdev_ms))}</Td>
            {[d.sector1_ms, d.sector2_ms, d.sector3_ms].map((s, i) => {
              const best = bestOf(s);
              return (
                <Td key={i} align="right" className="timing">
                  {best == null ? <Dash label="No sector time" /> : (best / 1000).toFixed(3)}
                </Td>
              );
            })}
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}

