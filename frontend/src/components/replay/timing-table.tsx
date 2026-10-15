"use client";

import { memo, useMemo, useRef } from "react";
import { EM_DASH } from "@/lib/format";
import { compoundInfo, formatReplayGap } from "@/lib/replay/format";
import { frameAt, frameIndexAt } from "@/lib/replay/frame";
import type { PlaybackController } from "@/lib/replay/controller";
import type { GapValue, ReplayDoc, ReplayDriver } from "@/lib/replay/types";
import { DataTable, Th } from "@/components/ui/data-table";
import { TeamBar } from "@/components/ui/entity-links";
import { usePlayback } from "./use-playback";
import { useFlip } from "./use-flip";

type RowProps = {
  driver: ReplayDriver;
  place: number;
  gap: GapValue;
  interval: GapValue;
  lap: number | null;
  tyre: string | null;
  tyreAge: number | null;
  pitStops: number;
  inPit: boolean;
  retired: boolean;
};

export function TyreBadge({ compound, age }: { compound: string | null; age: number | null }) {
  const info = compoundInfo(compound);
  if (!info) return <span aria-label="Tyre unknown">{EM_DASH}</span>;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        title={info.name}
        className={`inline-grid size-5 place-items-center rounded-full border-2 text-[0.7rem] font-extrabold leading-none ${info.className}`}
      >
        <span aria-hidden="true">{info.letter}</span>
        <span className="sr-only">{info.name}</span>
      </span>
      <span className="timing text-muted">
        {age == null ? EM_DASH : `${age}`}
        <span className="sr-only"> laps old</span>
      </span>
    </span>
  );
}

/** Memoised: with primitive props a row re-renders only when one of its own cells changed. */
const ReplayRow = memo(function ReplayRow({ driver, place, gap, interval, lap, tyre, tyreAge, pitStops, inPit, retired }: RowProps) {
  return (
    <tr data-id={driver.driver_id} className="border-b border-line bg-surface last:border-b-0" style={{ willChange: "transform" }}>
      <td className="timing w-12 px-3 py-2 text-right font-bold">{place || EM_DASH}</td>
      <th scope="row" className="px-3 py-2 text-left font-bold">
        <span className="inline-flex items-center gap-2">
          <TeamBar color={driver.color_hex} />
          <abbr title={driver.full_name} className="no-underline">
            {driver.code}
          </abbr>
          {inPit && !retired && (
            <span className="rounded bg-accent-soft px-1 text-[0.65rem] font-bold text-accent">
              PIT<span className="sr-only"> in the pit lane</span>
            </span>
          )}
        </span>
      </th>
      <td className="timing px-3 py-2 text-right">{retired ? "OUT" : place === 1 ? "Leader" : formatReplayGap(gap)}</td>
      <td className="timing px-3 py-2 text-right">{retired || place === 1 ? EM_DASH : formatReplayGap(interval)}</td>
      <td className="px-3 py-2">
        <TyreBadge compound={tyre} age={tyreAge} />
      </td>
      <td className="timing px-3 py-2 text-right">{pitStops}</td>
      <td className="timing px-3 py-2 text-right">{lap ?? EM_DASH}</td>
    </tr>
  );
});

export function TimingTable({
  doc,
  controller,
  caption,
}: {
  doc: ReplayDoc;
  controller: PlaybackController;
  caption: string;
}) {
  const frameIndex = usePlayback(controller, (s) => frameIndexAt(doc, s.t));
  const frame = useMemo(() => frameAt(doc, frameIndex * doc.frames.step_s), [doc, frameIndex]);
  const order = useMemo(() => frame.rows.map((r) => r.driverId).join(","), [frame]);
  const body = useRef<HTMLTableSectionElement>(null);
  useFlip(body, order, frameIndex);

  return (
    <DataTable caption={caption} minWidth="40rem">
      <thead>
        <tr>
          <Th align="right">Pos</Th>
          <Th>Driver</Th>
          <Th align="right">Gap</Th>
          <Th align="right">Int</Th>
          <Th>Tyre (age)</Th>
          <Th align="right">Stops</Th>
          <Th align="right">Lap</Th>
        </tr>
      </thead>
      <tbody ref={body}>
        {frame.rows.map((r, i) => (
          <ReplayRow
            key={r.driverId}
            driver={doc.drivers[r.driverIndex]}
            place={r.position == null ? 0 : i + 1}
            gap={r.gap}
            interval={r.interval}
            lap={r.lap}
            tyre={r.tyre}
            tyreAge={r.tyreAge}
            pitStops={r.pitStops}
            inPit={r.inPit}
            retired={r.retired}
          />
        ))}
      </tbody>
    </DataTable>
  );
}
