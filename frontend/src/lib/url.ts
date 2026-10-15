/** Helpers to keep list state (filters, sorting, page) in the URL. */

export type SearchParams = Record<string, string | string[] | undefined>;

export function first(value: string | string[] | undefined): string | undefined {
  const v = Array.isArray(value) ? value[0] : value;
  // Plain-object lookups such as sp.constructor can hit Object.prototype: only strings count.
  const t = typeof v === "string" ? v.trim() : undefined;
  return t ? t : undefined;
}

export function parseIntParam(
  value: string | string[] | undefined,
  { min = 1, max = Number.MAX_SAFE_INTEGER }: { min?: number; max?: number } = {},
): number | undefined {
  const v = first(value);
  if (!v || !/^\d+$/.test(v)) return undefined;
  const n = Number(v);
  return n >= min && n <= max ? n : undefined;
}

export function parseChoice<T extends string>(
  value: string | string[] | undefined,
  allowed: readonly T[],
  fallback: T,
): T {
  const v = first(value);
  return v && (allowed as readonly string[]).includes(v) ? (v as T) : fallback;
}

/** Build "/path?a=1&b=2", dropping empty values. */
export function buildHref(path: string, params: Record<string, string | number | undefined | null>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    usp.set(k, String(v));
  }
  const qs = usp.toString();
  return qs ? `${path}?${qs}` : path;
}

export type SortState = { field: string; desc: boolean };

export function parseSort(ordering: string): SortState {
  return ordering.startsWith("-") ? { field: ordering.slice(1), desc: true } : { field: ordering, desc: false };
}

/**
 * Next ordering when a header is clicked: first click sorts ascending for text
 * columns and descending for numeric ones, a second click flips it.
 */
export function nextOrdering(current: string, field: string, numeric: boolean): string {
  const s = parseSort(current);
  if (s.field === field) return s.desc ? field : `-${field}`;
  return numeric ? `-${field}` : field;
}

/** Slugs from the API are lowercase ASCII with dashes or underscores. Anything else is a 404. */
export function isSlug(value: string): boolean {
  return /^[a-z0-9][a-z0-9_-]{0,99}$/i.test(value);
}

/** Own-property lookup: `sp.constructor` would otherwise return Object.prototype.constructor. */
export function param(sp: SearchParams, key: string): string | string[] | undefined {
  return Object.hasOwn(sp, key) ? sp[key] : undefined;
}

/**
 * Season filter of the driver list: the latest season by default (the list is most useful for
 * the people racing now), but only while nothing else is filtered. `?season=all` shows everyone.
 */
export function resolveSeasonFilter({
  season,
  latest,
  hasOtherFilters,
}: {
  season: string | string[] | undefined;
  latest: number | undefined;
  hasOtherFilters: boolean;
}): { season: number | undefined; defaulted: boolean } {
  const explicit = parseIntParam(season, { min: 1950, max: 2100 });
  if (explicit) return { season: explicit, defaulted: false };
  const everyone = first(season) === "all";
  if (everyone || hasOtherFilters || latest === undefined) return { season: undefined, defaulted: false };
  return { season: latest, defaulted: true };
}
