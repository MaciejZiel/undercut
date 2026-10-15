import { createApiClient, type components } from "@/lib/api/client";
import type { AnalyticsSessionType } from "@/lib/api/queries";
import { formatLapTime } from "@/lib/format";

type S = components["schemas"];

export type Positions = S["Positions"];
export type Laps = S["Laps"];
export type Stints = S["Stints"];
export type PitStops = S["PitStops"];
export type Weather = S["Weather"];
export type RaceControl = S["RaceControl"];
export type Neutralisation = S["Neutralisation"];

export type AnalyticsRef = { year: number; round: number; session: AnalyticsSessionType };

/** HTTP failure of an analytics request. `analyticsAvailable` is the API's answer on a 404. */
export class AnalyticsError extends Error {
  constructor(
    readonly status: number,
    readonly analyticsAvailable: boolean | null = null,
  ) {
    super(`Analytics request failed (${status})`);
  }
}

function unwrap<T>(res: { data?: T; error?: unknown; response: Response }): T {
  if (res.data !== undefined && res.response.ok) return res.data;
  const err = res.error as { analytics_available?: boolean } | undefined;
  throw new AnalyticsError(res.response.status, typeof err?.analytics_available === "boolean" ? err.analytics_available : null);
}

function base(ref: AnalyticsRef) {
  return { path: { year: ref.year, round: ref.round } };
}

export async function fetchPositions(ref: AnalyticsRef): Promise<Positions> {
  const api = createApiClient(window.location.origin);
  return unwrap(
    await api.GET("/api/v1/rounds/{year}/{round}/analytics/positions/", {
      params: { ...base(ref), query: { session: ref.session } },
    }),
  );
}

export async function fetchLaps(ref: AnalyticsRef, drivers: string[], hideSlow: boolean): Promise<Laps> {
  const api = createApiClient(window.location.origin);
  return unwrap(
    await api.GET("/api/v1/rounds/{year}/{round}/analytics/laps/", {
      params: { ...base(ref), query: { session: ref.session, drivers: drivers.join(","), hide_slow: hideSlow } },
    }),
  );
}

export async function fetchStints(ref: AnalyticsRef): Promise<Stints> {
  const api = createApiClient(window.location.origin);
  return unwrap(
    await api.GET("/api/v1/rounds/{year}/{round}/analytics/stints/", {
      params: { ...base(ref), query: { session: ref.session } },
    }),
  );
}

export async function fetchPitStops(ref: AnalyticsRef): Promise<PitStops> {
  const api = createApiClient(window.location.origin);
  return unwrap(
    await api.GET("/api/v1/rounds/{year}/{round}/analytics/pit-stops/", {
      params: { ...base(ref), query: { session: ref.session } },
    }),
  );
}

export async function fetchWeather(ref: AnalyticsRef): Promise<Weather> {
  const api = createApiClient(window.location.origin);
  return unwrap(
    await api.GET("/api/v1/rounds/{year}/{round}/analytics/weather/", {
      params: { ...base(ref), query: { session: ref.session } },
    }),
  );
}

export async function fetchRaceControl(ref: AnalyticsRef): Promise<RaceControl> {
  const api = createApiClient(window.location.origin);
  return unwrap(
    await api.GET("/api/v1/rounds/{year}/{round}/analytics/race-control/", {
      params: { ...base(ref), query: { session: ref.session } },
    }),
  );
}

/** Query key shared by all views: one cache entry per session and view. */
export function analyticsKey(kind: string, ref: AnalyticsRef, ...extra: (string | boolean)[]) {
  return ["analytics", kind, ref.year, ref.round, ref.session, ...extra] as const;
}

// ---- pure transformations -------------------------------------------------------------------

const HEX = /^#[0-9a-fA-F]{6}$/;

/** Team colour from the API; null or malformed means the neutral colour. */
export function teamColor(hex: string | null | undefined, neutral: string): string {
  return hex && HEX.test(hex) ? hex : neutral;
}

/** Driver codes ordered by final position (last known position); drivers without data go last. */
export function finishingOrder(data: Positions): string[] {
  const finalPos = (d: Positions["drivers"][number]) => {
    for (let i = d.positions.length - 1; i >= 0; i--) {
      const p = d.positions[i];
      if (p != null) return p;
    }
    return Number.POSITIVE_INFINITY;
  };
  return data.drivers
    .map((d, i) => ({ code: d.code, pos: finalPos(d), i }))
    .sort((a, b) => a.pos - b.pos || a.i - b.i)
    .map((d) => d.code);
}

export function defaultLapDrivers(data: Positions, n = 3): string[] {
  return finishingOrder(data).slice(0, n);
}

/** [lap, position] pairs; a missing position stays null so the line breaks instead of dropping to 0. */
export function positionPairs(laps: number[], positions: (number | null)[]): [number, number | null][] {
  return laps.map((lap, i) => [lap, positions[i] ?? null]);
}

/** Vertical background bands for SC and VSC periods, padded by half a lap on both sides. */
export function neutralisationBands(items: Neutralisation[]): { kind: "SC" | "VSC"; from: number; to: number }[] {
  return items
    .filter((n) => n.end_lap >= n.start_lap)
    .map((n) => ({ kind: n.kind, from: n.start_lap - 0.5, to: n.end_lap + 0.5 }));
}

/** Teammates share a colour: the second driver of a constructor gets a dashed line. */
export function dashedDrivers(drivers: { code: string; constructor_id: number }[]): Set<string> {
  const seen = new Set<number>();
  const dashed = new Set<string>();
  for (const d of drivers) {
    if (seen.has(d.constructor_id)) dashed.add(d.code);
    else seen.add(d.constructor_id);
  }
  return dashed;
}

export type StintSegment = {
  stint: number;
  compound: string;
  letter: string;
  laps: number;
  lapStart: number;
  lapEnd: number;
  /** Percent of the race distance. */
  left: number;
  width: number;
};

export function totalLaps(data: Stints): number {
  let max = 0;
  for (const d of data.drivers) {
    let cursor = 0;
    for (const s of [...d.stints].sort((a, b) => a.stint_number - b.stint_number)) {
      const laps = s.laps ?? (s.lap_start != null && s.lap_end != null ? s.lap_end - s.lap_start + 1 : 0);
      const start0 = s.lap_start != null ? s.lap_start - 1 : cursor;
      cursor = start0 + laps;
    }
    max = Math.max(max, cursor);
  }
  return max;
}

/** Stint bars as percentages of the race distance. Stints without any laps are skipped. */
export function stintSegments(stints: S["Stint"][], total: number): StintSegment[] {
  if (total <= 0) return [];
  const out: StintSegment[] = [];
  let cursor = 0;
  for (const s of [...stints].sort((a, b) => a.stint_number - b.stint_number)) {
    const laps = s.laps ?? (s.lap_start != null && s.lap_end != null ? s.lap_end - s.lap_start + 1 : 0);
    const start0 = s.lap_start != null ? s.lap_start - 1 : cursor;
    cursor = start0 + laps;
    if (laps <= 0) continue;
    out.push({
      stint: s.stint_number,
      compound: s.compound,
      letter: s.compound_letter,
      laps,
      lapStart: start0 + 1,
      lapEnd: start0 + laps,
      left: (start0 / total) * 100,
      width: (laps / total) * 100,
    });
  }
  return out;
}

/** Drivers ordered by final classification, unclassified last. */
export function stintRows(data: Stints) {
  return data.drivers
    .map((d, i) => ({ d, i }))
    .sort((a, b) => (a.d.position ?? Infinity) - (b.d.position ?? Infinity) || a.i - b.i)
    .map(({ d }) => d);
}

export const COMPOUND_STYLE: Record<string, { label: string; bg: string; fg: string }> = {
  SOFT: { label: "Soft", bg: "#e5322d", fg: "#ffffff" },
  MEDIUM: { label: "Medium", bg: "#f2c200", fg: "#1a1400" },
  HARD: { label: "Hard", bg: "#e6e8ee", fg: "#10131c" },
  INTERMEDIATE: { label: "Intermediate", bg: "#2fae5b", fg: "#04170b" },
  WET: { label: "Wet", bg: "#2a6fdb", fg: "#ffffff" },
  UNKNOWN: { label: "Unknown", bg: "#8a93a6", fg: "#0b0f19" },
};

export function compoundStyle(compound: string | null | undefined) {
  return COMPOUND_STYLE[(compound ?? "").toUpperCase()] ?? COMPOUND_STYLE.UNKNOWN;
}

export function compoundLetter(compound: string | null | undefined): string {
  const l = (compound ?? "").charAt(0).toUpperCase();
  if (!compound) return "?";
  return compound.toUpperCase() === "INTERMEDIATE" ? "I" : l || "?";
}

/** 2.345 s style duration for pit stops; null stays null. */
export function formatSeconds(ms: number | null | undefined, digits = 3): string | null {
  if (ms == null || !Number.isFinite(ms)) return null;
  return `${(ms / 1000).toFixed(digits)} s`;
}

export function methodLabel(method: PitStops["method"]): string {
  return method === "lane_duration" ? "pit lane duration" : "stop duration";
}

/** Best (minimum) non-null value of a sector series. */
export function bestOf(values: (number | null)[]): number | null {
  let best: number | null = null;
  for (const v of values) if (v != null && (best === null || v < best)) best = v;
  return best;
}

export function lapRows(d: Laps["drivers"][number]) {
  return d.lap_numbers.map((lap, i) => ({
    lap: lap as number,
    ms: d.duration_ms[i] ?? null,
  }));
}

/** Rows lap by lap, one column per driver, for the table alternative of the lap chart. */
export function lapMatrix(data: Laps): { lap: number; times: (number | null)[] }[] {
  const byLap = new Map<number, (number | null)[]>();
  data.drivers.forEach((d, col) => {
    d.lap_numbers.forEach((lap, i) => {
      if (lap == null) return;
      let row = byLap.get(lap);
      if (!row) {
        row = data.drivers.map(() => null);
        byLap.set(lap, row);
      }
      row[col] = d.duration_ms[i] ?? null;
    });
  });
  return [...byLap.entries()].sort((a, b) => a[0] - b[0]).map(([lap, times]) => ({ lap, times }));
}

export function lapAxisLabel(ms: number): string {
  return formatLapTime(ms) ?? "";
}
