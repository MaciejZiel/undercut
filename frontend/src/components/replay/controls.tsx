"use client";

import { formatClock, SPEEDS } from "@/lib/replay/format";
import { lapAtTime } from "@/lib/replay/frame";
import type { PlaybackController } from "@/lib/replay/controller";
import { usePlayback } from "./use-playback";

const btn =
  "t-fast rounded-md border border-line bg-surface px-3 py-1.5 text-sm font-bold hover:bg-surface-2 aria-pressed:border-accent aria-pressed:bg-accent-soft aria-pressed:text-accent";

export const SEEK_STEP_S = 10;

export function Controls({
  controller,
  laps,
  totalLaps,
  duration,
}: {
  controller: PlaybackController;
  laps: { lap: number; t: number }[];
  totalLaps: number | null;
  duration: number;
}) {
  const playing = usePlayback(controller, (s) => s.playing);
  const speed = usePlayback(controller, (s) => s.speed);
  const clock = usePlayback(controller, (s) => Math.floor(s.t));
  const currentLap = usePlayback(controller, (s) => lapAtTime(laps, s.t) ?? 0);

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      <div className="flex items-center gap-2">
        <button type="button" className={btn} onClick={() => controller.seekBy(-SEEK_STEP_S)} aria-label={`Back ${SEEK_STEP_S} seconds`}>
          <span aria-hidden="true">&laquo;</span>
        </button>
        <button type="button" className={`${btn} min-w-20`} onClick={() => controller.toggle()}>
          {playing ? "Pause" : "Play"}
        </button>
        <button type="button" className={btn} onClick={() => controller.seekBy(SEEK_STEP_S)} aria-label={`Forward ${SEEK_STEP_S} seconds`}>
          <span aria-hidden="true">&raquo;</span>
        </button>
      </div>

      <div role="group" aria-label="Playback speed" className="flex items-center gap-1">
        {SPEEDS.map((s) => (
          <button
            key={s}
            type="button"
            className={btn}
            aria-pressed={speed === s}
            aria-label={`Speed ${s}x`}
            onClick={() => controller.setSpeed(s)}
          >
            {s}x
          </button>
        ))}
      </div>

      <label className="flex items-center gap-2 text-sm font-semibold">
        Jump to lap
        <select
          className="rounded-md border border-line bg-surface px-2 py-1.5 text-sm"
          value={currentLap || ""}
          onChange={(e) => {
            const target = laps.find((l) => l.lap === Number(e.target.value));
            if (target) controller.seek(target.t);
          }}
        >
          {currentLap === 0 && <option value="">Lap</option>}
          {laps.map((l) => (
            <option key={l.lap} value={l.lap}>
              {l.lap}
            </option>
          ))}
        </select>
      </label>

      <p className="timing ml-auto text-sm font-bold">
        <span className="sr-only">Race time </span>
        {formatClock(clock)} <span className="text-muted">/ {formatClock(duration)}</span>
        {totalLaps ? (
          <span className="ml-3">
            Lap {currentLap || 1}
            <span className="text-muted"> / {totalLaps}</span>
          </span>
        ) : null}
      </p>
    </div>
  );
}
