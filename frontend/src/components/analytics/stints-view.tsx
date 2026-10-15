"use client";

import { DataTable, RowTh, Td, Th, Tr } from "@/components/ui/data-table";
import {
  COMPOUND_STYLE,
  compoundStyle,
  fetchStints,
  stintRows,
  stintSegments,
  totalLaps,
  type AnalyticsRef,
  type Stints,
} from "./data";
import { ChartFrame, RequestState } from "./chart-frame";
import { useAnalytics } from "./hooks";

export function StintsView({ refs }: { refs: AnalyticsRef }) {
  const query = useAnalytics("stints", refs, () => fetchStints(refs));
  return (
    <RequestState
      query={query}
      isEmpty={(d) => d.drivers.every((x) => x.stints.length === 0)}
      emptyTitle="No tyre strategy data"
      emptyDescription="Stints appear here once tyre data has been processed."
    >
      {(data) => <StintsPanel data={data} />}
    </RequestState>
  );
}

const LEGEND = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"] as const;

function CompoundLegend() {
  return (
    <ul aria-label="Tyre compounds" className="flex flex-wrap gap-2 lg:flex-col">
      {LEGEND.map((c) => {
        const s = COMPOUND_STYLE[c];
        return (
          <li key={c} className="inline-flex items-center gap-2 text-sm font-semibold">
            <span
              aria-hidden="true"
              className="grid size-6 place-items-center rounded border border-line text-sm font-extrabold"
              style={{ backgroundColor: s.bg, color: s.fg }}
            >
              {c === "INTERMEDIATE" ? "I" : c[0]}
            </span>
            {s.label}
          </li>
        );
      })}
    </ul>
  );
}

function StintsPanel({ data }: { data: Stints }) {
  const title = `${data.session.year} ${data.session.round_name}: tyre strategy`;
  return (
    <ChartFrame
      title={title}
      zoomable={false}
      legend={<CompoundLegend />}
      chart={<StintBars data={data} />}
      table={<StintsTable data={data} />}
    />
  );
}

/** Horizontal stint bars: width is the share of race distance, the letter carries the compound. */
export function StintBars({ data }: { data: Stints }) {
  const total = totalLaps(data);
  const rows = stintRows(data);
  return (
    <div className="h-full overflow-auto" role="list" aria-label="Tyre stints by driver, in finishing order">
      {rows.map((d) => (
        <div key={d.code} role="listitem" className="mb-1.5 flex items-center gap-2">
          <span className="w-12 shrink-0 text-sm font-bold">{d.code}</span>
          <div className="relative h-7 flex-1 rounded bg-surface-2">
            {stintSegments(d.stints, total).map((s) => {
              const st = compoundStyle(s.compound);
              return (
                <span
                  key={s.stint}
                  title={`${st.label}, laps ${s.lapStart} to ${s.lapEnd} (${s.laps})`}
                  className="absolute inset-y-0 flex items-center justify-center overflow-hidden whitespace-nowrap rounded-sm border border-bg text-sm font-extrabold"
                  style={{ left: `${s.left}%`, width: `${s.width}%`, backgroundColor: st.bg, color: st.fg }}
                >
                  {s.letter}
                  <span className="timing ml-1 font-semibold opacity-80">{s.laps}</span>
                  <span className="sr-only">
                    {st.label} tyre, {s.laps} laps
                  </span>
                </span>
              );
            })}
          </div>
        </div>
      ))}
      <div className="ml-14 flex justify-between text-sm text-muted" aria-hidden="true">
        <span>Lap 1</span>
        <span>Lap {total}</span>
      </div>
    </div>
  );
}

export function StintsTable({ data }: { data: Stints }) {
  return (
    <DataTable caption="Tyre stints per driver" minWidth="32rem">
      <thead>
        <tr>
          <Th align="right">Pos</Th>
          <Th>Driver</Th>
          <Th>Stints (compound, laps)</Th>
        </tr>
      </thead>
      <tbody>
        {stintRows(data).map((d) => (
          <Tr key={d.code}>
            <Td align="right" className="timing font-bold">{d.position ?? "–"}</Td>
            <RowTh className="font-semibold">{d.code}</RowTh>
            <Td>
              {d.stints
                .map((s) => `${s.compound_letter} ${compoundStyle(s.compound).label}, laps ${s.lap_start ?? "?"}-${s.lap_end ?? "?"} (${s.laps ?? "?"})`)
                .join("; ")}
            </Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}
