/** Time and label helpers of the calendar. Pure functions, no clock access. */

export const SESSION_LABELS: Record<string, string> = {
  FP1: "Practice 1",
  FP2: "Practice 2",
  FP3: "Practice 3",
  SQ: "Sprint qualifying",
  SPRINT: "Sprint",
  Q: "Qualifying",
  RACE: "Race",
};

export function sessionLabel(type: string): string {
  return SESSION_LABELS[type] ?? type;
}

const STATUS_LABELS: Record<string, string> = {
  completed: "Completed",
  next: "Next",
  upcoming: "Upcoming",
  cancelled: "Cancelled",
};

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

/** The IANA name when the runtime knows it, otherwise null. */
export function safeZone(zone: string | null | undefined): string | null {
  if (!zone) return null;
  try {
    new Intl.DateTimeFormat("en-GB", { timeZone: zone });
    return zone;
  } catch {
    return null;
  }
}

/** "Sat 15 Mar, 16:00 CET" in the given zone; null for a missing or invalid instant. */
export function formatSessionTime(iso: string | null | undefined, zone: string): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  const timeZone = safeZone(zone) ?? "UTC";
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone,
    timeZoneName: "short",
  }).format(date);
}

/** Plain link to the Django endpoint; served as text/calendar, so the browser handles the download. */
export function icsHref(year: number, round?: number | null): string {
  const params = new URLSearchParams({ year: String(year) });
  if (round != null) params.set("round", String(round));
  return `/api/v1/calendar/ics/?${params.toString()}`;
}
