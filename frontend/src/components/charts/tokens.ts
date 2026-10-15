/** Chart colours come from the CSS variables of the active theme, never hard-coded. */
export type ChartTokens = {
  fg: string;
  muted: string;
  line: string;
  surface: string;
  accent: string;
  /** Colour-blind friendly categorical palette, readable on both themes. */
  palette: string[];
};

const FALLBACK: ChartTokens = {
  fg: "#1d1e1b",
  muted: "#5a5851",
  line: "#cbc7bc",
  surface: "#e9e5d9",
  accent: "#b8341a",
  palette: [],
};

const LIGHT_PALETTE = ["#b8341a", "#1f4e79", "#2a7f62", "#b07a00", "#7a4a8c", "#0b7285", "#8a5a3c", "#5a5851", "#d6603b", "#3d6b2e"];
const DARK_PALETTE = ["#ff7a5c", "#7fb2e5", "#4fcf9f", "#e6b84a", "#c79be0", "#4fc3d6", "#d49a7a", "#a8a59c", "#ffa17f", "#8fd16f"];

function isDark(root: HTMLElement): boolean {
  const explicit = root.getAttribute("data-theme");
  if (explicit === "dark") return true;
  if (explicit === "light") return false;
  return typeof window.matchMedia === "function" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function readChartTokens(root: HTMLElement = document.documentElement): ChartTokens {
  const css = getComputedStyle(root);
  const get = (name: string, fallback: string) => css.getPropertyValue(name).trim() || fallback;
  return {
    fg: get("--fg", FALLBACK.fg),
    muted: get("--fg-muted", FALLBACK.muted),
    line: get("--line", FALLBACK.line),
    surface: get("--surface", FALLBACK.surface),
    accent: get("--accent", FALLBACK.accent),
    palette: isDark(root) ? DARK_PALETTE : LIGHT_PALETTE,
  };
}

/** Colour of the i-th series; wraps around. */
export function seriesColor(tokens: ChartTokens, index: number): string {
  const p = tokens.palette.length ? tokens.palette : LIGHT_PALETTE;
  return p[((index % p.length) + p.length) % p.length];
}
