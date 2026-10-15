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

/** The sessions of one weekend in the viewer's time zone, with the race picked out in flag yellow. */
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
      <h3 id="schedule-h" className="label mb-1.5">
        Weekend schedule
      </h3>
      <table className="w-full border-collapse text-left">
        <caption className="sr-only">Session times in your time zone ({zone})</caption>
        <tbody>
          {rows.map((s) => {
            const date = new Date(s.startMs);
            const race = s.type === "RACE";
            const live = relativeLabel(s.startMs, s.endMs, now) === "on now";
            return (
              <tr key={s.type} className={race ? "bg-flag text-on-flag" : "border-t border-line"}>
                <th scope="row" className="w-[3.4rem] py-3 pl-2.5 pr-2 text-left text-sm font-normal text-muted">
                  <span className={race ? "text-on-flag" : ""}>{part(date, zone, { weekday: "short" })}</span>
                </th>
                <td className="mono w-[4.6rem] py-3 text-[0.9375rem]">{part(date, zone, { hour: "2-digit", minute: "2-digit", hourCycle: "h23" })}</td>
                <td className="py-3 font-semibold">{sessionLabel(s.type)}</td>
                <td className={`py-3 pr-2.5 text-right text-sm ${race ? "text-on-flag" : "text-muted"} ${live ? "font-bold" : ""}`}>
                  {relativeLabel(s.startMs, s.endMs, now)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-3 text-sm text-muted">Times in your time zone ({zone.replace("_", " ")}).</p>
    </section>
  );
}
