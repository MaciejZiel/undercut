/**
 * Views of the round page next to the plain results. Data-driven: to add a view (for example
 * the replay) append one entry here and render it in the page.
 */
export type RoundViewKey = "results" | "positions" | "laps" | "tyres" | "pits" | "weather" | "control" | "replay";

export type RoundViewDef = {
  key: string;
  label: string;
  /** Needs detailed (OpenF1) data, so it is offered only from the 2023 season. */
  analytics: boolean;
};

export const ROUND_VIEWS: RoundViewDef[] = [
  { key: "results", label: "Results", analytics: false },
  { key: "positions", label: "Positions", analytics: true },
  { key: "laps", label: "Lap times", analytics: true },
  { key: "tyres", label: "Tyres", analytics: true },
  { key: "pits", label: "Pit stops", analytics: true },
  { key: "weather", label: "Weather", analytics: true },
  { key: "control", label: "Race control", analytics: true },
  { key: "replay", label: "Replay", analytics: true },
];

/** Links from before the views were flattened keep working. */
const LEGACY: Record<string, string> = { analysis: "positions", strategy: "tyres" };

export const ANALYTICS_FROM_SEASON = 2023;

export function visibleViews(year: number, views: RoundViewDef[] = ROUND_VIEWS): RoundViewDef[] {
  return views.filter((v) => !v.analytics || year >= ANALYTICS_FROM_SEASON);
}

export function pickView(requested: string | undefined, year: number, views: RoundViewDef[] = ROUND_VIEWS): string {
  const key = requested ? (LEGACY[requested] ?? requested) : requested;
  return visibleViews(year, views).find((v) => v.key === key)?.key ?? "results";
}

/** Round URL with the session and view in the query; defaults stay out of the URL. */
export function viewHref(base: string, opts: { session?: string | null; view?: string }): string {
  const q = new URLSearchParams();
  if (opts.session) q.set("session", opts.session);
  if (opts.view && opts.view !== "results") q.set("view", opts.view);
  const s = q.toString();
  return s ? `${base}?${s}` : base;
}
