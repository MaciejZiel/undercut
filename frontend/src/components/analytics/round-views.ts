/**
 * Views of the round page next to the plain results. Data-driven: to add a view (for example
 * the replay) append one entry here and render it in the page.
 */
export type RoundViewKey = "results" | "analysis" | "strategy";

export type RoundViewDef = {
  key: string;
  label: string;
  /** Needs detailed (OpenF1) data, so it is offered only from the 2023 season. */
  analytics: boolean;
};

export const ROUND_VIEWS: RoundViewDef[] = [
  { key: "results", label: "Results", analytics: false },
  { key: "analysis", label: "Analysis", analytics: true },
  { key: "strategy", label: "Strategy", analytics: true },
  { key: "replay", label: "Replay", analytics: true },
];

export const ANALYTICS_FROM_SEASON = 2023;

export function visibleViews(year: number, views: RoundViewDef[] = ROUND_VIEWS): RoundViewDef[] {
  return views.filter((v) => !v.analytics || year >= ANALYTICS_FROM_SEASON);
}

export function pickView(requested: string | undefined, year: number, views: RoundViewDef[] = ROUND_VIEWS): string {
  return visibleViews(year, views).find((v) => v.key === requested)?.key ?? "results";
}

/** Round URL with the session and view in the query; defaults stay out of the URL. */
export function viewHref(base: string, opts: { session?: string | null; view?: string }): string {
  const q = new URLSearchParams();
  if (opts.session) q.set("session", opts.session);
  if (opts.view && opts.view !== "results") q.set("view", opts.view);
  const s = q.toString();
  return s ? `${base}?${s}` : base;
}
