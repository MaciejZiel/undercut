import { EM_DASH } from "@/lib/format";
import type { GapValue } from "./types";

/** 12345 -> "+12.345", 75000 -> "+1:15.000", "+1 LAP" stays, null -> em dash. */
export function formatReplayGap(value: GapValue): string {
  if (value == null) return EM_DASH;
  if (typeof value === "string") return value.trim() || EM_DASH;
  if (!Number.isFinite(value) || value < 0) return EM_DASH;
  const total = Math.round(value);
  const minutes = Math.floor(total / 60000);
  const seconds = Math.floor((total % 60000) / 1000);
  const millis = String(total % 1000).padStart(3, "0");
  return minutes > 0 ? `+${minutes}:${String(seconds).padStart(2, "0")}.${millis}` : `+${seconds}.${millis}`;
}

export type Compound = { letter: string; name: string; className: string };

const COMPOUNDS: Record<string, Compound> = {
  SOFT: { letter: "S", name: "Soft", className: "border-red-500 text-red-600 dark:text-red-400" },
  MEDIUM: { letter: "M", name: "Medium", className: "border-yellow-500 text-yellow-700 dark:text-yellow-300" },
  HARD: { letter: "H", name: "Hard", className: "border-fg text-fg" },
  INTERMEDIATE: { letter: "I", name: "Intermediate", className: "border-green-600 text-green-700 dark:text-green-400" },
  WET: { letter: "W", name: "Wet", className: "border-blue-500 text-blue-600 dark:text-blue-400" },
};

/** Compound letter, name and colour classes; null for unknown or missing data. The letter always carries the meaning. */
export function compoundInfo(raw: string | null | undefined): Compound | null {
  if (!raw) return null;
  return COMPOUNDS[raw.trim().toUpperCase()] ?? null;
}

/** "0:05" under an hour, "1:02:03" above. Whole seconds. */
export function formatClock(seconds: number): string {
  const s = Math.max(0, Math.floor(Number.isFinite(seconds) ? seconds : 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = String(s % 60).padStart(2, "0");
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`;
}

export const SPEEDS = [1, 5, 20, 60] as const;
export type Speed = (typeof SPEEDS)[number];
