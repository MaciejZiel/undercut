export type SessionKey = "race" | "sprint" | "qualifying" | "sprint-qualifying" | "fp3" | "fp2" | "fp1";
export type ApiSessionType = "RACE" | "SPRINT" | "Q" | "SQ" | "FP1" | "FP2" | "FP3";

export type SessionTab = { key: SessionKey; type: ApiSessionType; label: string; core: boolean };

/** In the order the tabs are shown: the sessions that decide the weekend first, practice last. */
const ALL_TABS: SessionTab[] = [
  { key: "race", type: "RACE", label: "Race", core: true },
  { key: "sprint", type: "SPRINT", label: "Sprint", core: true },
  { key: "qualifying", type: "Q", label: "Qualifying", core: true },
  { key: "sprint-qualifying", type: "SQ", label: "Sprint qualifying", core: false },
  { key: "fp3", type: "FP3", label: "Practice 3", core: false },
  { key: "fp2", type: "FP2", label: "Practice 2", core: false },
  { key: "fp1", type: "FP1", label: "Practice 1", core: false },
];

type SessionInfo = { type: string; has_results: boolean };

/**
 * Tabs for the sessions that exist in this weekend. Race, sprint and qualifying always show (an empty
 * one explains itself); sprint qualifying and practice show once they have results.
 */
export function availableTabs(sessions: SessionInfo[]): SessionTab[] {
  return ALL_TABS.filter((t) => {
    const info = sessions.find((s) => s.type === t.type);
    return info !== undefined && (t.core || info.has_results);
  });
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
