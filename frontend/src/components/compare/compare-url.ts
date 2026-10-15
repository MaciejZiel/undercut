import { buildHref } from "@/lib/url";

export type CompareState = { a: string | null; b: string | null; season: number | null };

export const COMPARE_PATH = "/compare";
export const MIN_SEASON = 1950;
export const MAX_SEASON = 2100;

/** Driver slug from the query string: lowercase letters, digits, dashes and underscores only. */
export function parseSlug(value: string | string[] | undefined): string | null {
  const v = Array.isArray(value) ? value[0] : value;
  return typeof v === "string" && /^[\w-]{1,100}$/.test(v) ? v : null;
}

export function parseSeason(value: string | string[] | undefined): number | null {
  const v = Array.isArray(value) ? value[0] : value;
  if (typeof v !== "string" || !/^\d{4}$/.test(v)) return null;
  const n = Number(v);
  return n >= MIN_SEASON && n <= MAX_SEASON ? n : null;
}

export function compareHref(state: CompareState): string {
  return buildHref(COMPARE_PATH, { a: state.a, b: state.b, season: state.season });
}

/** The comparison can be requested only for two different drivers. */
export function isReady(state: CompareState): state is { a: string; b: string; season: number | null } {
  return state.a !== null && state.b !== null && state.a !== state.b;
}
