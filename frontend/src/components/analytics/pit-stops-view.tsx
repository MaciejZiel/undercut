"use client";

import { DataTable, RowTh, Td, Th, Tr } from "@/components/ui/data-table";
import { orDash } from "@/components/ui/value";
import { compoundLetter, fetchPitStops, formatSeconds, methodLabel, type AnalyticsRef, type PitStops } from "./data";
import { RequestState } from "./chart-frame";
import { useAnalytics } from "./hooks";

export function PitStopsView({ refs }: { refs: AnalyticsRef }) {
  const query = useAnalytics("pit-stops", refs, () => fetchPitStops(refs));
  return (
    <RequestState
      query={query}
      isEmpty={(d) => d.stops.length === 0}
      emptyTitle="No pit stops"
      emptyDescription="Pit stops appear here once the session has been processed."
    >
      {(data) => <PitStopsPanel data={data} />}
    </RequestState>
  );
}

function change(from: string | null, to: string | null) {
  if (!from && !to) return null;
  return `${compoundLetter(from)} → ${compoundLetter(to)}`;
}

function PitStopsPanel({ data }: { data: PitStops }) {
  const method = methodLabel(data.method);
  return (
    <div className="space-y-6">
      <section aria-labelledby="pit-rank-h">
        <h3 id="pit-rank-h" className="text-base font-extrabold tracking-tight">
          Fastest pit stops by team
        </h3>
        <p className="mb-2 text-sm text-muted">Ranked by {method}, each team&apos;s best stop.</p>
        <DataTable caption={`Team ranking of the fastest pit stops by ${method}`} minWidth="30rem">
          <thead>
            <tr>
              <Th align="right">Rank</Th>
              <Th>Team</Th>
              <Th>Driver</Th>
              <Th align="right">Lap</Th>
              <Th align="right">Time ({method})</Th>
            </tr>
          </thead>
          <tbody>
            {data.ranking.map((r) => (
              <Tr key={r.constructor_id}>
                <Td align="right" className="timing font-bold">{r.rank}</Td>
                <RowTh>{r.constructor_name}</RowTh>
                <Td>{r.driver_code}</Td>
                <Td align="right" className="timing">{orDash(r.lap)}</Td>
                <Td align="right" className="timing">{orDash(formatSeconds(r.duration_ms))}</Td>
              </Tr>
            ))}
          </tbody>
        </DataTable>
      </section>
      <section aria-labelledby="pit-all-h">
        <h3 id="pit-all-h" className="mb-2 text-base font-extrabold tracking-tight">
          All pit stops
        </h3>
        <DataTable caption="All pit stops" minWidth="38rem">
          <thead>
            <tr>
              <Th>Driver</Th>
              <Th>Team</Th>
              <Th align="right">Lap</Th>
              <Th align="right">Stop</Th>
              <Th align="right">Pit lane</Th>
              <Th>Tyres</Th>
            </tr>
          </thead>
          <tbody>
            {data.stops.map((s, i) => (
              <Tr key={`${s.driver_code}-${s.lap}-${i}`}>
                <RowTh className="font-semibold">{s.driver_code}</RowTh>
                <Td>{s.constructor_name}</Td>
                <Td align="right" className="timing">{orDash(s.lap)}</Td>
                <Td align="right" className="timing">{orDash(formatSeconds(s.stop_ms))}</Td>
                <Td align="right" className="timing">{orDash(formatSeconds(s.lane_ms))}</Td>
                <Td className="timing">{orDash(change(s.compound_from, s.compound_to), "Unknown")}</Td>
              </Tr>
            ))}
          </tbody>
        </DataTable>
        <p className="mt-2 text-xs text-muted">Data: OpenF1</p>
      </section>
    </div>
  );
}
