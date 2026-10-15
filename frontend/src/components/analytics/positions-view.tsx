"use client";

import { useMemo, useState } from "react";
import { readChartTokens, type ChartTokens } from "@/components/charts/tokens";
import { DataTable, RowTh, Td, Th, Tr } from "@/components/ui/data-table";
import { Dash } from "@/components/ui/value";
import { dashedDrivers, fetchPositions, teamColor, type AnalyticsRef, type Positions } from "./data";
import { AnalyticsChart, ChartFrame, RequestState } from "./chart-frame";
import { useAnalytics } from "./hooks";
import { buildPositionsOption } from "./options";

export function PositionsView({ refs }: { refs: AnalyticsRef }) {
  const query = useAnalytics("positions", refs, () => fetchPositions(refs));
  return (
    <RequestState
      query={query}
      isEmpty={(d) => d.drivers.length === 0 || d.laps.length === 0}
      emptyTitle="No lap-by-lap positions"
      emptyDescription="Positions appear here once lap data has been processed."
    >
      {(data) => <PositionsPanel data={data} />}
    </RequestState>
  );
}

function PositionsPanel({ data }: { data: Positions }) {
  const [highlight, setHighlight] = useState<string | null>(null);
  const option = useMemo(() => (t: ChartTokens) => buildPositionsOption(data, highlight, t), [data, highlight]);
  const dashed = useMemo(() => dashedDrivers(data.drivers), [data]);
  const title = `${data.session.year} ${data.session.round_name}: position by lap`;
  const neutral = readChartTokens().muted;

  const legend = (
    <ul aria-label="Drivers" className="flex flex-wrap gap-1.5 lg:flex-col lg:flex-nowrap">
      {data.drivers.map((d) => {
        const on = highlight === d.code;
        const faded = highlight !== null && !on;
        return (
          <li key={d.code}>
            <button
              type="button"
              aria-pressed={on}
              onClick={() => setHighlight(on ? null : d.code)}
              title={`${d.full_name}, ${d.constructor_name}`}
              className={`t-fast inline-flex w-full items-center gap-2 rounded-sm border px-2 py-1 text-sm font-semibold ${
                on ? "border-accent bg-accent-soft text-fg" : "border-line text-fg"
              } ${faded ? "opacity-40" : ""}`}
            >
              <span
                aria-hidden="true"
                className="inline-block w-5 border-t-[3px]"
                style={{ borderColor: teamColor(d.color_hex, neutral), borderTopStyle: dashed.has(d.code) ? "dashed" : "solid" }}
              />
              {d.code}
            </button>
          </li>
        );
      })}
    </ul>
  );

  return (
    <ChartFrame
      title={title}
      legend={legend}
      chart={<AnalyticsChart option={option} label={`${title}. Pit stops are marked with dots; safety car periods are shaded. A table is available.`} />}
      table={<PositionsTable data={data} />}
    />
  );
}

/** Table alternative: one row per lap, one column per driver. */
export function PositionsTable({ data }: { data: Positions }) {
  return (
    <div className="max-h-[32rem] overflow-auto rounded-sm">
      <DataTable caption="Position of every driver at the end of each lap" minWidth={`${6 + data.drivers.length * 3}rem`}>
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
          {data.laps.map((lap, i) => (
            <Tr key={lap}>
              <RowTh className="timing text-right font-bold">{lap}</RowTh>
              {data.drivers.map((d) => {
                const p = d.positions[i];
                const pit = d.pit_laps.includes(lap);
                return (
                  <Td key={d.code} align="right" className="timing">
                    {p == null ? <Dash label="No position" /> : p}
                    {pit && <span title="Pit stop"> P<span className="sr-only"> pit stop</span></span>}
                  </Td>
                );
              })}
            </Tr>
          ))}
        </tbody>
      </DataTable>
    </div>
  );
}
