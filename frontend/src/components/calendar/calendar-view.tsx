"use client";

import Link from "next/link";
import { useState } from "react";
import type { components } from "@/lib/api/client";
import { formatDayMonth } from "@/lib/format";
import { circuitHref, roundHref } from "@/lib/routes";
import { Countdown } from "@/components/dashboard/countdown";
import { Badge } from "@/components/ui/entity-links";
import { Dash } from "@/components/ui/value";
import { formatSessionTime, icsHref, safeZone, sessionLabel, statusLabel } from "./time";
import { useViewerZone } from "./use-viewer-zone";

type Entry = components["schemas"]["CalendarEntry"];
type Mode = "viewer" | "circuit";

const MODES: { value: Mode; label: string }[] = [
  { value: "viewer", label: "My time zone" },
  { value: "circuit", label: "Circuit local time" },
];

export function CalendarView({ year, rounds }: { year: number; rounds: Entry[] }) {
  const viewerZone = useViewerZone();
  const [mode, setMode] = useState<Mode>("viewer");

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div role="group" aria-label="Time zone of session times" className="flex gap-1">
          {MODES.map((m) => (
            <button
              key={m.value}
              type="button"
              aria-pressed={mode === m.value}
              onClick={() => setMode(m.value)}
              className={`t-fast rounded-md border px-3.5 py-2 text-sm font-bold ${
                mode === m.value ? "border-accent bg-accent text-accent-fg" : "border-line-strong text-accent hover:border-accent hover:bg-surface"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
        <p className="text-sm text-muted" aria-live="polite">
          {mode === "viewer" ? `Times shown in ${viewerZone}.` : "Times shown in each circuit's local time."}
        </p>
      </div>
      <ol className="border-t border-line">
        {rounds.map((entry, i) => (
          <RoundCard key={`${entry.round ?? "x"}-${i}`} year={year} entry={entry} mode={mode} viewerZone={viewerZone} />
        ))}
      </ol>
    </div>
  );
}

function RoundCard({ year, entry, mode, viewerZone }: { year: number; entry: Entry; mode: Mode; viewerZone: string }) {
  const cancelled = entry.status === "cancelled";
  const completed = entry.status === "completed";
  const highlight = entry.is_next && !cancelled;
  const circuitZone = safeZone(entry.circuit.timezone);
  const zone = mode === "circuit" && circuitZone ? circuitZone : viewerZone;
  const fallback = mode === "circuit" && !circuitZone;
  const headId = `round-${entry.round ?? "x"}-${entry.date}`;
  const tone = cancelled ? "danger" : entry.status === "next" ? "accent" : "neutral";

  return (
    <li className="border-b border-line">
      <article
        aria-labelledby={headId}
        aria-current={highlight ? "step" : undefined}
        className={`grid grid-cols-[3.5rem_minmax(0,1fr)] gap-x-4 gap-y-3 py-4 sm:grid-cols-[4.5rem_minmax(0,1fr)_auto] sm:gap-x-6 ${
          highlight ? "-mx-3 rounded-xl bg-surface px-3 sm:-mx-5 sm:px-5 sm:py-5" : ""
        } ${cancelled ? "text-muted" : ""}`}
      >
        <p className="timing leading-tight text-muted">
          <span className="block text-xs">{entry.round != null ? `Round ${entry.round}` : "Round"}</span>
          <span className="mt-1 block text-sm font-bold text-fg">{formatDayMonth(entry.date) ?? <Dash />}</span>
        </p>
        <div className="min-w-0">
          <h2 id={headId} className={`heading ${completed || cancelled ? "text-xl" : "text-2xl"}`}>
            {entry.round != null && !cancelled ? (
              <Link href={roundHref(year, entry.round)} className="hover:text-accent hover:underline">
                {entry.name}
              </Link>
            ) : (
              entry.name
            )}
          </h2>
          <p className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
            <span>
              <Link href={circuitHref(entry.circuit.slug)} className="font-semibold hover:text-accent hover:underline">
                {entry.circuit.name}
              </Link>
              {entry.circuit.country ? `, ${entry.circuit.country}` : ""}
            </span>
            <Badge tone={tone}>{statusLabel(entry.status)}</Badge>
            {entry.has_sprint && <Badge>Sprint</Badge>}
          </p>
          {highlight && (
            <div className="mt-4">
              {entry.race_start_utc ? <Countdown target={entry.race_start_utc} /> : <p className="text-sm text-muted">Start time to be confirmed</p>}
            </div>
          )}
          {!cancelled && !completed && (
            <div className="mt-3">
              {entry.sessions.length === 0 ? (
                <p className="text-sm text-muted">Session times have not been published yet.</p>
              ) : (
                <>
                  <ul aria-label={`Sessions of ${entry.name}`} className="grid grid-cols-1 gap-x-8 text-sm sm:grid-cols-2">
                    {entry.sessions.map((s) => {
                      const when = formatSessionTime(s.start_utc, zone);
                      return (
                        <li key={s.type} className="flex justify-between gap-3 border-b border-line py-1.5 last:border-b-0 sm:[&:nth-last-child(2):nth-child(odd)]:border-b-0">
                          <span className="font-semibold">{sessionLabel(s.type)}</span>
                          {when && s.start_utc ? (
                            <time dateTime={s.start_utc} className="timing text-right">
                              {when}
                            </time>
                          ) : (
                            <Dash label="Time to be confirmed" />
                          )}
                        </li>
                      );
                    })}
                  </ul>
                  {fallback && <p className="mt-1 text-xs text-muted">Circuit time zone unknown, showing your time zone.</p>}
                </>
              )}
            </div>
          )}
        </div>
        {!cancelled && !completed && entry.round != null && (
          <a
            href={icsHref(year, entry.round)}
            className="t-fast col-start-2 inline-flex min-h-10 items-center self-start justify-self-start rounded-md border border-line-strong px-3.5 text-sm font-bold text-accent hover:border-accent hover:bg-bg sm:col-start-3 sm:row-start-1"
          >
            Add to calendar
            <span className="sr-only">: {entry.name}</span>
          </a>
        )}
      </article>
    </li>
  );
}
