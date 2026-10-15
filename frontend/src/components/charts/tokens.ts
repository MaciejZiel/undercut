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
  fg: "#203149",
  muted: "#5d6b7e",
  line: "#dce3ed",
  surface: "#f0f5fc",
  accent: "#244d8e",
  palette: [],
};

const LIGHT_PALETTE = ["#244d8e", "#d55e00", "#0072b2", "#009e73", "#cc79a7", "#8a6d00", "#56b4e9", "#b3261e", "#5d6b7e", "#117733"];
const DARK_PALETTE = ["#8fb4f0", "#ff9f4a", "#56b4e9", "#3ddc97", "#f28dc0", "#e6c84a", "#7fd0ff", "#ff8a80", "#9ba8c1", "#6fd08c"];

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
