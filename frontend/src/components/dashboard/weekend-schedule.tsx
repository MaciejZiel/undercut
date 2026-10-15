"use client";

import type { components } from "@/lib/api/client";
import { sessionLabel } from "@/components/calendar/time";
import { useViewerZone } from "@/components/calendar/use-viewer-zone";
import { useNow } from "./use-now";

type Session = components["schemas"]["CalendarSession"];

const HOUR = 3_600_000;
const DAY = 24 * HOUR;

function part(date: Date, zone: string, options: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat("en-GB", { ...options, timeZone: zone }).format(date);
}

/** "in 3 days", "in 5 h", "in 40 min", "on now" or "done", from the clock. Empty until the clock exists. */
export function relativeLabel(startMs: number, endMs: number | null, now: number | null): string {
  if (now === null) return "";
  if (now >= startMs && (endMs === null || now < endMs)) return "on now";
  if (endMs !== null && now >= endMs) return "done";
  if (now >= startMs) return "done";
  const diff = startMs - now;
  if (diff >= 2 * DAY) return `in ${Math.floor(diff / DAY)} days`;
  if (diff >= HOUR) return `in ${Math.floor(diff / HOUR)} h`;
  return `in ${Math.max(1, Math.floor(diff / 60_000))} min`;
}

function clock(date: Date, zone: string): { time: string; zone: string } {
  const parts = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZoneName: "short", timeZone: zone }).formatToParts(date);
  const pick = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return { time: `${pick("hour")}:${pick("minute")}`, zone: pick("timeZoneName") };
}

/** The sessions of one weekend in the viewer's time zone; the race is set in blue and bold. */
export function WeekendSchedule({ sessions }: { sessions: Session[] }) {
  const zone = useViewerZone();
  const now = useNow(30_000);
  const rows = sessions
    .filter((s) => s.start_utc)
    .map((s) => ({ ...s, startMs: Date.parse(s.start_utc as string), endMs: s.end_utc ? Date.parse(s.end_utc) : null }))
    .filter((s) => !Number.isNaN(s.startMs))
    .sort((a, b) => a.startMs - b.startMs);
  if (rows.length === 0) return null;
  return (
    <section aria-labelledby="schedule-h">
      <h4 id="schedule-h" className="sr-only">
        Sessions
      </h4>
      <table className="w-full border-collapse text-left">
        <caption className="sr-only">Session times in your time zone ({zone})</caption>
        <tbody>
          {rows.map((s) => {
            const date = new Date(s.startMs);
            const race = s.type === "RACE";
            const label = relativeLabel(s.startMs, s.endMs, now);
            const time = clock(date, zone);
            return (
              <tr key={s.type} className="border-b border-line last:border-b-0">
                <th scope="row" className="w-14 py-3 pr-3 text-left align-middle font-normal text-muted">
                  <span className="block text-xs leading-tight">{part(date, zone, { weekday: "short" })}</span>
                  <span className="block text-lg font-semibold leading-tight text-fg">{part(date, zone, { day: "numeric" })}</span>
                </th>
                <td className={`py-3 pr-3 align-middle text-sm font-semibold ${race ? "text-accent" : ""}`}>
                  {sessionLabel(s.type)}
                  {label === "on now" && (
                    <span className="ml-2 rounded-sm bg-flag px-1.5 py-0.5 align-middle text-xs font-bold text-on-flag">On now</span>
                  )}
                </td>
                <td className="py-3 text-right align-middle">
                  <span className={`block text-base font-extrabold leading-tight tabular-nums ${race ? "text-accent" : ""}`}>{time.time}</span>
                  <span className="block text-xs leading-tight text-muted">
                    {time.zone}
                    {label && label !== "on now" ? ` · ${label}` : ""}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-3 text-xs text-muted">Times in your time zone ({zone.replace("_", " ")}).</p>
    </section>
  );
}
