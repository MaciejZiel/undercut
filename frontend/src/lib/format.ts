/** Formatting helpers. Null never becomes 0: callers render EM_DASH for missing values. */

export const EM_DASH = "—";

const pad = (n: number, width = 2) => String(n).padStart(width, "0");

/** Lap or qualifying time: 83456 -> "1:23.456", 59123 -> "59.123". */
export function formatLapTime(ms: number | null | undefined): string | null {
  if (ms == null || !Number.isFinite(ms) || ms < 0) return null;
  const total = Math.round(ms);
  const minutes = Math.floor(total / 60000);
  const seconds = Math.floor((total % 60000) / 1000);
  const millis = total % 1000;
  return minutes > 0 ? `${minutes}:${pad(seconds)}.${pad(millis, 3)}` : `${seconds}.${pad(millis, 3)}`;
}

/** Winner's total race time: 5527123 -> "1:32:07.123". */
export function formatRaceTime(ms: number | null | undefined): string | null {
  if (ms == null || !Number.isFinite(ms) || ms < 0) return null;
  const total = Math.round(ms);
  const hours = Math.floor(total / 3_600_000);
  const minutes = Math.floor((total % 3_600_000) / 60000);
  const seconds = Math.floor((total % 60000) / 1000);
  const millis = total % 1000;
  return hours > 0
    ? `${hours}:${pad(minutes)}:${pad(seconds)}.${pad(millis, 3)}`
    : `${minutes}:${pad(seconds)}.${pad(millis, 3)}`;
}

/** Gap to the leader: 5234 -> "+5.234", 75000 -> "+1:15.000". */
export function formatGap(ms: number | null | undefined): string | null {
  const t = formatLapTime(ms);
  return t === null ? null : `+${t}`;
}

type Timed = { position: number | null; time_ms: number | null; laps: number | null; status: string | null };

/**
 * Gap behind the winner. The API sends every finisher's total race time, so the gap is the difference to
 * the winner's time. A driver who finished laps down has no meaningful time gap and shows the laps instead;
 * a driver who retired has none at all.
 */
export function formatRaceGap(result: Timed, winner: Timed | undefined): string | null {
  if (result.time_ms == null) return null;
  if (result.position === 1 || winner == null) return formatRaceTime(result.time_ms);
  if (winner.laps != null && result.laps != null && result.laps < winner.laps) {
    const down = winner.laps - result.laps;
    return result.status === "Lapped" ? `+${down} ${down === 1 ? "lap" : "laps"}` : null;
  }
  if (winner.time_ms == null || result.time_ms < winner.time_ms) return null;
  return formatGap(result.time_ms - winner.time_ms);
}

export type PositionChange = {
  direction: "up" | "down" | "same";
  amount: number;
  /** Arrow glyph. */
  symbol: string;
  /** Screen reader and tooltip text. */
  label: string;
};

/** Grid minus finish, as sent by the API: positive means places gained. Null stays null. */
export function describePositionChange(change: number | null | undefined): PositionChange | null {
  if (change == null || !Number.isFinite(change)) return null;
  if (change > 0) {
    return {
      direction: "up",
      amount: change,
      symbol: "▲",
      label: `Gained ${change} ${change === 1 ? "place" : "places"}`,
    };
  }
  if (change < 0) {
    const n = Math.abs(change);
    return {
      direction: "down",
      amount: n,
      symbol: "▼",
      label: `Lost ${n} ${n === 1 ? "place" : "places"}`,
    };
  }
  return { direction: "same", amount: 0, symbol: "–", label: "Position unchanged" };
}

/** Championship points: 25 -> "25", 12.5 -> "12.5", 1234.5 -> "1,234.5". */
export function formatPoints(points: number | null | undefined): string | null {
  if (points == null || !Number.isFinite(points)) return null;
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(points);
}

export function formatInteger(value: number | null | undefined): string | null {
  if (value == null || !Number.isFinite(value)) return null;
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value);
}

/** Circuit length in metres -> "5.412 km". */
export function formatLength(meters: number | null | undefined): string | null {
  if (meters == null || !Number.isFinite(meters)) return null;
  return `${(meters / 1000).toFixed(3)} km`;
}

/** ISO date (YYYY-MM-DD) -> "12 Mar 2023", always UTC so server and browser agree. */
export function formatDate(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return null;
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(d);
}

/** "12 Mar" without the year, for calendars that already show the season. */
export function formatDayMonth(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return null;
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" }).format(d);
}

/** Display position: a number, or the retirement code ("R", "D", "W") when there is none. */
export function formatPosition(position: number | null, positionText: string | null): string | null {
  if (position != null) return String(position);
  return positionText ? positionText : null;
}

export function fullName(d: { given_name: string; family_name: string }): string {
  return `${d.given_name} ${d.family_name}`.trim();
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
