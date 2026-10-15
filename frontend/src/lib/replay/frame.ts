import type { DriverFrames, FrameState, ReplayDoc, RowState, Runs } from "./types";

/** Index of the last entry of `at` that is <= index, or -1. Binary search. */
export function runIndex(at: readonly number[], index: number): number {
  let lo = 0;
  let hi = at.length - 1;
  let found = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >>> 1;
    if (at[mid] <= index) {
      found = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return found;
}

/** Value of a run encoded series at a frame index (carry-forward). */
export function runValue<T>(runs: Runs<T>, index: number): T | null {
  const k = runIndex(runs.at, index);
  return k < 0 ? null : runs.v[k];
}

/** Frame in effect at time t: floor(t / step), clamped to the document. */
export function frameIndexAt(doc: Pick<ReplayDoc, "frames">, tSeconds: number): number {
  const { step_s, count } = doc.frames;
  if (count <= 0) return 0;
  if (!Number.isFinite(tSeconds) || tSeconds <= 0) return 0;
  return Math.min(count - 1, Math.floor(tSeconds / step_s));
}

/** Last time that can be played (time of the final frame). */
export function lastFrameT(doc: Pick<ReplayDoc, "frames">): number {
  const { step_s, count } = doc.frames;
  return Math.max(0, (count - 1) * step_s);
}

/** Number of pit stops started up to a frame: rising edges 0 -> 1 of the run encoded `pit`. */
export function pitStopsAt(pit: Runs<number>, index: number): number {
  const last = runIndex(pit.at, index);
  let stops = 0;
  for (let k = 0; k <= last; k++) if (pit.v[k] === 1 && (k === 0 || pit.v[k - 1] !== 1)) stops++;
  return stops;
}

function rowAt(doc: ReplayDoc, k: number, f: DriverFrames, index: number, t: number): RowState {
  const driver = doc.drivers[k];
  return {
    driverIndex: k,
    driverId: driver.driver_id,
    position: f.pos[index] ?? null,
    gap: f.gap[index] ?? null,
    interval: f.int[index] ?? null,
    lap: runValue(f.lap, index),
    tyre: runValue(f.tyre, index),
    tyreAge: runValue(f.age, index),
    inPit: runValue(f.pit, index) === 1,
    pitStops: pitStopsAt(f.pit, index),
    retired: driver.retired_t != null && t >= driver.retired_t,
  };
}

/**
 * Timing table state at a time. Pure; nothing is interpolated: every value is the last
 * known sample at or before the frame (the backend already carries values forward).
 * Cost is O(drivers * (log runs + pit runs)) plus the sort of the rows.
 */
export function frameAt(doc: ReplayDoc, tSeconds: number): FrameState {
  const index = frameIndexAt(doc, tSeconds);
  const frameT = doc.frames.t[index] ?? index * doc.frames.step_s;
  const rows: RowState[] = [];
  const count = Math.min(doc.drivers.length, doc.frames.drivers.length);
  for (let k = 0; k < count; k++) rows.push(rowAt(doc, k, doc.frames.drivers[k], index, tSeconds));
  rows.sort((a, b) => {
    const pa = a.position ?? Number.POSITIVE_INFINITY;
    const pb = b.position ?? Number.POSITIVE_INFINITY;
    return pa - pb || a.driverIndex - b.driverIndex;
  });
  let leaderLap: number | null = null;
  for (const r of rows) if (r.lap != null && (leaderLap === null || r.lap > leaderLap)) leaderLap = r.lap;
  return { index, frameT, rows, leaderLap };
}

/** Lap number whose start is the latest one at or before t, from the jump-to-lap helper. */
export function lapAtTime(laps: readonly { lap: number; t: number }[], tSeconds: number): number | null {
  let found: number | null = null;
  for (const l of laps) {
    if (l.t <= tSeconds) found = l.lap;
    else break;
  }
  return found;
}

/** Jump-to-lap table derived from the document: lap number -> earliest frame time any driver is on it. */
export function lapStarts(doc: ReplayDoc): { lap: number; t: number }[] {
  const earliest = new Map<number, number>();
  const step = doc.frames.step_s;
  for (const f of doc.frames.drivers) {
    for (let k = 0; k < f.lap.at.length; k++) {
      const lap = f.lap.v[k];
      if (lap == null) continue;
      const t = f.lap.at[k] * step;
      const prev = earliest.get(lap);
      if (prev === undefined || t < prev) earliest.set(lap, t);
    }
  }
  return [...earliest.entries()].sort((a, b) => a[0] - b[0]).map(([lap, t]) => ({ lap, t }));
}
