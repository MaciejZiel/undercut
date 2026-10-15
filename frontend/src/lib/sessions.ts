export type SessionKey = "race" | "sprint" | "qualifying";
export type ApiSessionType = "RACE" | "SPRINT" | "Q";

export type SessionTab = { key: SessionKey; type: ApiSessionType; label: string };

const ALL_TABS: SessionTab[] = [
  { key: "qualifying", type: "Q", label: "Qualifying" },
  { key: "sprint", type: "SPRINT", label: "Sprint" },
  { key: "race", type: "RACE", label: "Race" },
];

type SessionInfo = { type: string; has_results: boolean };

/** Tabs for the sessions that exist in this weekend, race first. */
export function availableTabs(sessions: SessionInfo[]): SessionTab[] {
  const present = new Set(sessions.map((s) => s.type));
  return [...ALL_TABS].reverse().filter((t) => present.has(t.type));
}

/**
 * The requested tab if the weekend has it. Otherwise the race if it has
 * results, else the first session that has results, else the first tab.
 */
export function pickTab(requested: string | undefined, tabs: SessionTab[], sessions: SessionInfo[]): SessionTab | null {
  const wanted = tabs.find((t) => t.key === requested);
  if (wanted) return wanted;
  const withResults = tabs.filter((t) => sessions.some((s) => s.type === t.type && s.has_results));
  return withResults[0] ?? tabs[0] ?? null;
}

/** First tab (race) has no query parameter: its URL is the plain round URL. */
export function tabHref(base: string, tab: SessionTab, defaultTab: SessionTab | null): string {
  return tab.key === defaultTab?.key ? base : `${base}?session=${tab.key}`;
}
