"use client";

import { formatClock } from "@/lib/replay/format";
import type { PlaybackController } from "@/lib/replay/controller";
import type { ReplayEvent, ReplayEventKind } from "@/lib/replay/types";
import { usePlayback } from "./use-playback";

const KIND: Record<ReplayEventKind, { short: string; tone: string }> = {
  start: { short: "S", tone: "bg-fg text-bg" },
  pit: { short: "P", tone: "bg-muted text-bg" },
  safety_car: { short: "SC", tone: "bg-yellow-400/70 text-black" },
  vsc: { short: "VSC", tone: "bg-yellow-400/40 text-fg" },
  red_flag: { short: "R", tone: "bg-danger text-bg" },
  chequered: { short: "F", tone: "bg-fg text-bg" },
};

const pct = (t: number, duration: number) => `${Math.min(100, Math.max(0, duration > 0 ? (t / duration) * 100 : 0))}%`;

function describe(e: ReplayEvent) {
  return `${e.label}, lap ${e.lap}, ${formatClock(e.t)}`;
}

export function Timeline({
  controller,
  duration,
  events,
  laps,
}: {
  controller: PlaybackController;
  duration: number;
  events: ReplayEvent[];
  laps: { lap: number; t: number }[];
}) {
  const value = usePlayback(controller, (s) => Math.floor(s.t));
  const lapNow = laps.reduce((acc, l) => (l.t <= value ? l.lap : acc), 0);
  const pits = events.filter((e) => e.kind === "pit");
  const periods = events.filter((e) => (e.kind === "safety_car" || e.kind === "vsc") && e.end_t != null);
  const points = events.filter((e) => e.kind === "start" || e.kind === "red_flag" || e.kind === "chequered");

  return (
    <div>
      <div className="relative h-7" data-testid="timeline-markers">
        {periods.map((e, i) => (
          <button
            key={`${e.kind}-${i}`}
            type="button"
            title={describe(e)}
            aria-label={describe(e)}
            onClick={() => controller.seek(e.t)}
            className={`absolute top-0 h-5 min-w-5 overflow-hidden rounded-sm px-1 text-[0.6rem] font-extrabold leading-5 ${KIND[e.kind].tone}`}
            style={{ left: pct(e.t, duration), width: `max(1.25rem, calc(${pct((e.end_t ?? e.t) - e.t, duration)}))` }}
          >
            {KIND[e.kind].short}
          </button>
        ))}
        {pits.map((e, i) => (
          <span
            key={`pit-${i}`}
            aria-hidden="true"
            title={describe(e)}
            className="absolute bottom-0 h-2 w-px bg-muted"
            style={{ left: pct(e.t, duration) }}
          />
        ))}
        {points.map((e, i) => (
          <button
            key={`${e.kind}-${i}`}
            type="button"
            title={describe(e)}
            aria-label={describe(e)}
            onClick={() => controller.seek(e.t)}
            className={`absolute top-0 grid size-5 -translate-x-1/2 place-items-center rounded-full text-[0.6rem] font-extrabold ${KIND[e.kind].tone}`}
            style={{ left: pct(e.t, duration) }}
          >
            {KIND[e.kind].short}
          </button>
        ))}
      </div>
      <input
        type="range"
        min={0}
        max={Math.floor(duration)}
        step={1}
        value={value}
        onChange={(e) => controller.seek(Number(e.target.value))}
        aria-label="Timeline"
        aria-valuetext={`${formatClock(value)}${lapNow ? `, lap ${lapNow}` : ""}`}
        className="h-5 w-full cursor-pointer accent-[var(--accent)]"
      />
      <p className="mt-1 text-xs text-muted">
        Markers: S start, P pit stop (small ticks), SC safety car, VSC virtual safety car, R red flag, F chequered flag.
      </p>
      <details className="mt-2 text-sm">
        <summary className="cursor-pointer font-semibold">Race events ({events.length})</summary>
        <ul className="mt-2 grid max-h-56 gap-1 overflow-y-auto sm:grid-cols-2">
          {events.map((e, i) => (
            <li key={i}>
              <button
                type="button"
                onClick={() => controller.seek(e.t)}
                className="t-fast w-full rounded px-2 py-1 text-left hover:bg-surface-2"
              >
                <span className="timing mr-2 text-muted">{formatClock(e.t)}</span>
                {e.label} <span className="text-muted">(lap {e.lap})</span>
              </button>
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
