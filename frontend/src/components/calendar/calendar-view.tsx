"use client";

import Link from "next/link";
import { useState } from "react";
import type { components } from "@/lib/api/client";
import { formatDayMonth } from "@/lib/format";
import { circuitHref, roundHref } from "@/lib/routes";
import { Countdown } from "@/components/dashboard/countdown";
import { TeamBar } from "@/components/ui/entity-links";
import { driverHref } from "@/lib/routes";
import { Dash } from "@/components/ui/value";
import { AddToCalendar } from "./add-to-calendar";
import { formatSessionTime, safeZone, sessionLabel, statusLabel } from "./time";
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
  // Finished rounds fold away once the season has a round still to come, so "next" is the first thing seen.
  const firstOpen = rounds.findIndex((r) => r.status !== "completed" && r.status !== "cancelled");
  const done = firstOpen > 0 ? rounds.slice(0, firstOpen) : [];
  const open = firstOpen > 0 ? rounds.slice(firstOpen) : rounds;

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
      {done.length > 0 && (
        <details className="group mb-8 border-y border-fg">
          <summary className="t-fast flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 py-2 text-sm font-bold hover:text-accent">
            <span>
              {done.length} completed {done.length === 1 ? "round" : "rounds"}
            </span>
            <span className="eyebrow group-open:hidden">Show</span>
            <span className="eyebrow hidden group-open:inline">Hide</span>
          </summary>
          <Months year={year} rounds={done} mode={mode} viewerZone={viewerZone} />
        </details>
      )}
      <Months year={year} rounds={open} mode={mode} viewerZone={viewerZone} />
    </div>
  );
}

function Months({ year, rounds, mode, viewerZone }: { year: number; rounds: Entry[]; mode: Mode; viewerZone: string }) {
  return (
    <div>
      {groupByMonth(rounds).map((g) => (
        <section key={g.key} aria-labelledby={`month-${g.key}`} className="mt-8 first:mt-0">
          <h3 id={`month-${g.key}`} className="eyebrow mb-2">
            {g.label}
          </h3>
          <ol className="border-t border-line">
            {g.entries.map(({ entry, index }) => (
              <RoundCard key={`${entry.round ?? "x"}-${index}`} year={year} entry={entry} mode={mode} viewerZone={viewerZone} />
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}

/** Rounds grouped under their month, in calendar order. The month comes from the ISO date, so no time zone shifts it. */
function groupByMonth(rounds: Entry[]) {
  const groups: { key: string; label: string; entries: { entry: Entry; index: number }[] }[] = [];
  rounds.forEach((entry, index) => {
    const key = entry.date.slice(0, 7);
    let g = groups[groups.length - 1];
    if (!g || g.key !== key) {
      const label = new Intl.DateTimeFormat("en-GB", { month: "long", timeZone: "UTC" }).format(new Date(`${key}-01T00:00:00Z`));
      g = { key, label, entries: [] };
      groups.push(g);
    }
    g.entries.push({ entry, index });
  });
  return groups;
}

function RoundCard({ year, entry, mode, viewerZone }: { year: number; entry: Entry; mode: Mode; viewerZone: string }) {
  const cancelled = entry.status === "cancelled";
  const completed = entry.status === "completed";
  const highlight = entry.is_next && !cancelled;
  const circuitZone = safeZone(entry.circuit.timezone);
  const zone = mode === "circuit" && circuitZone ? circuitZone : viewerZone;
  const fallback = mode === "circuit" && !circuitZone;
  const headId = `round-${entry.round ?? "x"}-${entry.date}`;

  return (
    <li className="border-b border-line">
      <article
        aria-labelledby={headId}
        aria-current={highlight ? "step" : undefined}
        className={`grid grid-cols-[3.5rem_minmax(0,1fr)] gap-x-4 gap-y-3 py-4 sm:grid-cols-[4.5rem_minmax(0,1fr)_auto] sm:gap-x-6 ${
          highlight ? "-mx-3 bg-surface px-3 sm:-mx-5 sm:px-5 sm:py-5" : ""
        } ${cancelled ? "text-muted" : ""}`}
      >
        <p className="timing leading-tight text-muted">
          <span className="block text-xs">{entry.round != null ? `Round ${entry.round}` : "Round"}</span>
          <span className="mt-1 block text-sm font-bold text-fg">{formatDayMonth(entry.date) ?? <Dash />}</span>
        </p>
        <div className="min-w-0">
          <h2 id={headId} className={`heading ${completed || cancelled ? "text-lg" : "text-xl sm:text-[1.375rem]"}`}>
            {entry.round != null && !cancelled ? (
              <Link href={roundHref(year, entry.round)} className="rowlink hover:text-accent hover:underline">
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
            <span className={completed ? "sr-only" : `font-bold ${cancelled ? "text-danger" : entry.status === "next" ? "text-accent" : ""}`}>
              {statusLabel(entry.status)}
            </span>
            {entry.has_sprint && <span className="font-bold">Sprint</span>}
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
        {completed && entry.winner && (
          <p className="col-start-2 flex items-center text-sm sm:col-start-3 sm:row-start-1">
            <TeamBar color={entry.winner.team.color} />
            <span className="ml-2">
              <span className="text-muted">Won by </span>
              <Link href={driverHref(entry.winner.driver.slug)} className="font-bold hover:text-accent hover:underline">
                {entry.winner.driver.name}
              </Link>
            </span>
          </p>
        )}
        {!cancelled && !completed && entry.round != null && (
          <div className="col-start-2 self-start justify-self-start text-accent sm:col-start-3 sm:row-start-1 sm:justify-self-end">
            <AddToCalendar year={year} round={entry.round} label="Add to calendar" srName={entry.name} align="right" className="justify-start gap-1.5" />
          </div>
        )}
      </article>
    </li>
  );
}
