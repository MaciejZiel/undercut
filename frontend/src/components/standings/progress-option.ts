import type { Progress } from "@/lib/api/queries";
import type { EChartOption } from "@/components/charts/echart";
import { seriesColor, type ChartTokens } from "@/components/charts/tokens";

export type ProgressMetric = "points" | "position";

export const DEFAULT_VISIBLE = 5;

/** Slugs shown by default: the first `n` series (the API sorts by final standing). */
export function defaultSelection(data: Progress, n = DEFAULT_VISIBLE): string[] {
  return data.series.slice(0, n).map((s) => s.entity.slug);
}

/** Toggle a slug; always keeps the original series order so colours stay stable. */
export function toggleSelection(data: Progress, selected: string[], slug: string): string[] {
  const next = new Set(selected);
  if (next.has(slug)) next.delete(slug);
  else next.add(slug);
  return data.series.map((s) => s.entity.slug).filter((s) => next.has(s));
}

export function seriesValues(series: Progress["series"][number], metric: ProgressMetric): (number | null)[] {
  return metric === "points" ? series.points : series.positions;
}

const HEX = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

/**
 * The team's colour, the same one the tables and the race charts use. A driver whose team mate comes
 * earlier in the list gets a dashed line, so two lines of one colour can still be told apart.
 */
export function lineLook(data: Progress, index: number, tokens: ChartTokens): { color: string; dashed: boolean } {
  const s = data.series[index];
  const team = s.color && HEX.test(s.color) ? s.color : null;
  const dashed = team !== null && data.series.slice(0, index).some((o) => o.color === s.color);
  return { color: team ?? seriesColor(tokens, index), dashed };
}

/** Colours are tied to the index in the full list, so toggling a line never recolours the others. */
export function buildProgressOption(
  data: Progress,
  selected: string[],
  metric: ProgressMetric,
  tokens: ChartTokens,
): EChartOption {
  const chosen = new Set(selected);
  const lines = data.series
    .map((s, index) => ({ s, index }))
    .filter(({ s }) => chosen.has(s.entity.slug));
  const axisText = { color: tokens.muted, fontFamily: "IBM Plex Mono, ui-monospace, Menlo, monospace", fontSize: 11 };
  return {
    animation: false,
    textStyle: { color: tokens.fg },
    grid: { left: 8, right: 16, top: 32, bottom: 8, containLabel: true },
    tooltip: {
      trigger: "axis",
      confine: true,
      backgroundColor: tokens.surface,
      borderColor: tokens.fg,
      borderWidth: 1,
      extraCssText: "border-radius:0;box-shadow:none;",
      textStyle: { color: tokens.fg, fontSize: 12 },
      axisPointer: { type: "line", lineStyle: { color: tokens.line } },
    },
    xAxis: {
      type: "category",
      name: "Round",
      nameLocation: "middle",
      nameGap: 28,
      nameTextStyle: axisText,
      data: data.rounds.map(String),
      boundaryGap: false,
      axisLine: { lineStyle: { color: tokens.line } },
      axisLabel: axisText,
    },
    yAxis: {
      type: "value",
      name: metric === "points" ? "Points" : "Position",
      nameTextStyle: axisText,
      inverse: metric === "position",
      min: metric === "position" ? 1 : 0,
      max: metric === "position" ? Math.max(data.series.length, 2) : undefined,
      minInterval: 1,
      axisLabel: axisText,
      splitLine: { lineStyle: { color: tokens.line } },
    },
    series: lines.map(({ s, index }) => {
      const look = lineLook(data, index, tokens);
      return {
        name: s.entity.name,
        type: "line",
        data: seriesValues(s, metric),
        connectNulls: false,
        symbolSize: 6,
        itemStyle: { color: look.color },
        lineStyle: { width: 2.5, color: look.color, type: look.dashed ? "dashed" : "solid" },
      };
    }),
  };
}
