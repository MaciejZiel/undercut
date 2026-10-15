"use client";

import Link from "next/link";
import { useState } from "react";
import type { components } from "@/lib/api/client";
import { formatDate } from "@/lib/format";
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
              className={`t-fast rounded-md border px-3 py-1.5 text-sm font-semibold ${
                mode === m.value ? "border-accent bg-accent-soft text-accent" : "border-line bg-surface hover:bg-surface-2"
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
      <ol className="flex flex-col gap-4">
        {rounds.map((entry, i) => (
          <RoundCard key={`${entry.round ?? "x"}-${i}`} year={year} entry={entry} mode={mode} viewerZone={viewerZone} />
        ))}
      </ol>
    </div>
  );
}

function RoundCard({ year, entry, mode, viewerZone }: { year: number; entry: Entry; mode: Mode; viewerZone: string }) {
  const cancelled = entry.status === "cancelled";
  const highlight = entry.is_next && !cancelled;
  const circuitZone = safeZone(entry.circuit.timezone);
  const zone = mode === "circuit" && circuitZone ? circuitZone : viewerZone;
  const fallback = mode === "circuit" && !circuitZone;
  const headId = `round-${entry.round ?? "x"}-${entry.date}`;
  const tone = cancelled ? "danger" : entry.status === "next" ? "accent" : "neutral";

  return (
    <li>
      <article
        aria-labelledby={headId}
        aria-current={highlight ? "step" : undefined}
        className={`rounded-lg border bg-surface p-4 sm:p-5 ${highlight ? "border-accent ring-2 ring-accent" : "border-line"} ${cancelled ? "text-muted" : ""}`}
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="flex flex-wrap items-center gap-2 text-xs font-bold uppercase tracking-wide text-muted">
              <span className="timing">{entry.round != null ? `Round ${entry.round}` : "Round"}</span>
              <Badge tone={tone}>{statusLabel(entry.status)}</Badge>
              {entry.has_sprint && <Badge>Sprint</Badge>}
            </p>
            <h2 id={headId} className="mt-1 text-xl font-extrabold tracking-tight">
              {entry.round != null && !cancelled ? (
                <Link href={roundHref(year, entry.round)} className="hover:text-accent hover:underline">
                  {entry.name}
                </Link>
              ) : (
                entry.name
              )}
            </h2>
            <p className="mt-0.5 text-sm text-muted">
              <Link href={circuitHref(entry.circuit.slug)} className="font-semibold hover:text-accent hover:underline">
                {entry.circuit.name}
              </Link>
              {entry.circuit.country ? `, ${entry.circuit.country}` : ""}
            </p>
            <p className="timing text-sm text-muted">{formatDate(entry.date) ?? <Dash />}</p>
          </div>
          {!cancelled && entry.round != null && (
            <a
              href={icsHref(year, entry.round)}
              className="t-fast rounded-md border border-line px-3 py-1.5 text-sm font-semibold hover:bg-surface-2"
            >
              Add to calendar
              <span className="sr-only">: {entry.name}</span>
            </a>
          )}
        </div>

        {highlight && (
          <div className="mt-4">
            {entry.race_start_utc ? <Countdown target={entry.race_start_utc} /> : <p className="text-sm text-muted">Start time to be confirmed</p>}
          </div>
        )}

        {!cancelled && (
          <div className="mt-4">
            {entry.sessions.length === 0 ? (
              <p className="text-sm text-muted">Session times have not been published yet.</p>
            ) : (
              <>
                <ul aria-label={`Sessions of ${entry.name}`} className="grid grid-cols-1 gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
                  {entry.sessions.map((s) => {
                    const when = formatSessionTime(s.start_utc, zone);
                    return (
                      <li key={s.type} className="flex justify-between gap-3 border-b border-line py-1">
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
                {fallback && (
                  <p className="mt-1 text-xs text-muted">Circuit time zone unknown, showing your time zone.</p>
                )}
              </>
            )}
          </div>
        )}
      </article>
    </li>
  );
}
