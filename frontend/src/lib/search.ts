import type { components } from "@/lib/api/client";
import { formatDate } from "@/lib/format";
import { circuitHref, constructorHref, driverHref, roundHref } from "@/lib/routes";

export type SearchResponse = components["schemas"]["Search"];

export const MIN_QUERY_LENGTH = 2;
export const MAX_PER_GROUP = 5;

export type SuggestionItem = { id: string; href: string; label: string; detail: string | null };
export type SuggestionGroup = { key: "drivers" | "constructors" | "circuits" | "rounds"; label: string; items: SuggestionItem[] };

/** Groups in display order, at most `limit` per group, empty groups dropped. */
export function groupSuggestions(data: SearchResponse, limit = MAX_PER_GROUP): SuggestionGroup[] {
  const groups: SuggestionGroup[] = [
    {
      key: "drivers",
      label: "Drivers",
      items: (data.drivers ?? []).map((d) => ({
        id: `driver-${d.slug}`,
        href: driverHref(d.slug),
        label: d.name,
        detail: d.nationality ?? null,
      })),
    },
    {
      key: "constructors",
      label: "Constructors",
      items: (data.constructors ?? []).map((c) => ({
        id: `constructor-${c.slug}`,
        href: constructorHref(c.slug),
        label: c.name,
        detail: c.nationality ?? null,
      })),
    },
    {
      key: "circuits",
      label: "Circuits",
      items: (data.circuits ?? []).map((c) => ({
        id: `circuit-${c.slug}`,
        href: circuitHref(c.slug),
        label: c.name,
        detail: c.country ?? null,
      })),
    },
    {
      key: "rounds",
      label: "Races",
      items: (data.rounds ?? []).map((r) => ({
        id: `round-${r.year}-${r.round}`,
        href: roundHref(r.year, r.round),
        label: `${r.year} ${r.name}`,
        detail: formatDate(r.date),
      })),
    },
  ];
  return groups.map((g) => ({ ...g, items: g.items.slice(0, limit) })).filter((g) => g.items.length > 0);
}

export function searchHref(q: string): string {
  return `/search?q=${encodeURIComponent(q.trim())}`;
}
