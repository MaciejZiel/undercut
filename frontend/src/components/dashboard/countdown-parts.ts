import type { components } from "@/lib/api/client";

type CalendarRound = components["schemas"]["CalendarRound"];

/**
 * Next race: the first held round dated today or later without a winner.
 * Last race: the latest round that already has a winner.
 */
export function pickRaces(rounds: CalendarRound[], today: string): { next: CalendarRound | null; last: CalendarRound | null } {
  const held = rounds.filter((r) => !r.is_cancelled && r.round !== null).sort((a, b) => a.date.localeCompare(b.date));
  const next = held.find((r) => r.date >= today && !r.winner) ?? null;
  const done = held.filter((r) => r.winner);
  return { next, last: done.length ? done[done.length - 1] : null };
}

export type CountdownParts = { days: number; hours: number; minutes: number; seconds: number };

/** Split a remaining time into parts; null once the moment has passed. */
export function countdownParts(targetMs: number, nowMs: number): CountdownParts | null {
  const diff = Math.floor((targetMs - nowMs) / 1000);
  if (!Number.isFinite(diff) || diff <= 0) return null;
  return {
    days: Math.floor(diff / 86400),
    hours: Math.floor((diff % 86400) / 3600),
    minutes: Math.floor((diff % 3600) / 60),
    seconds: diff % 60,
  };
}
