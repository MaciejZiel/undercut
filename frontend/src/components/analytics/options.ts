import type { EChartOption } from "@/components/charts/echart";
import type { ChartTokens } from "@/components/charts/tokens";
import {
  dashedDrivers,
  neutralisationBands,
  positionPairs,
  teamColor,
  type Laps,
  type Positions,
  type Weather,
} from "./data";
import { formatLapTime } from "@/lib/format";

const FADED = 0.12;

function axisBits(tokens: ChartTokens) {
  const axisText = { color: tokens.muted };
  return {
    axisText,
    tooltip: {
      confine: true,
      backgroundColor: tokens.surface,
      borderColor: tokens.line,
      textStyle: { color: tokens.fg },
    },
    line: { lineStyle: { color: tokens.line } },
  };
}

/** Touch pinch and wheel zoom on the x axis; no visible slider so the canvas keeps its space. */
function zoom(): EChartOption[] {
  return [{ type: "inside", xAxisIndex: 0, filterMode: "none" }];
}

function bandAreas(bands: ReturnType<typeof neutralisationBands>, tokens: ChartTokens) {
  return bands.map((b) => [
    {
      name: b.kind,
      xAxis: b.from,
      itemStyle: { color: b.kind === "SC" ? "rgba(242,194,0,0.22)" : "rgba(242,194,0,0.10)" },
      label: { show: true, position: "insideTop", color: tokens.fg, fontSize: 11, fontWeight: 700 },
    },
    { xAxis: b.to },
  ]);
}

/** FR-401: one line per driver, position 1 on top, pit stops as dots, SC/VSC as background bands. */
export function buildPositionsOption(data: Positions, highlight: string | null, tokens: ChartTokens): EChartOption {
  const { axisText, tooltip, line } = axisBits(tokens);
  const dashed = dashedDrivers(data.drivers);
  const bands = bandAreas(neutralisationBands(data.neutralisations), tokens);
  const lastLap = data.laps.length ? data.laps[data.laps.length - 1] : 1;
  const firstLap = data.laps.length ? data.laps[0] : 1;
  return {
    animation: false,
    textStyle: { color: tokens.fg },
    grid: { left: 8, right: 20, top: 16, bottom: 8, containLabel: true },
    tooltip: { ...tooltip, trigger: "axis", axisPointer: { type: "line", lineStyle: { color: tokens.line } } },
    dataZoom: zoom(),
    xAxis: {
      type: "value",
      name: "Lap",
      nameLocation: "middle",
      nameGap: 28,
      nameTextStyle: axisText,
      min: firstLap,
      max: lastLap,
      minInterval: 1,
      axisLine: line,
      axisLabel: axisText,
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      name: "Position",
      nameTextStyle: axisText,
      inverse: true,
      min: 1,
      max: Math.max(data.drivers.length, 2),
      interval: 1,
      axisLabel: axisText,
      splitLine: { lineStyle: { color: tokens.line } },
    },
    series: data.drivers.map((d, index) => {
      const pits = new Set(d.pit_laps);
      const faded = highlight !== null && highlight !== d.code;
      const color = teamColor(d.color_hex, tokens.muted);
      return {
        name: d.code,
        type: "line",
        color,
        z: highlight === d.code ? 5 : 2,
        connectNulls: false,
        symbol: "none",
        data: positionPairs(data.laps, d.positions).map(([lap, pos]) =>
          pits.has(lap) && pos != null
            ? { value: [lap, pos], symbol: "circle", symbolSize: 9, itemStyle: { color: tokens.surface, borderColor: color, borderWidth: 2 } }
            : [lap, pos],
        ),
        lineStyle: { width: highlight === d.code ? 3.5 : 2, type: dashed.has(d.code) ? "dashed" : "solid", opacity: faded ? FADED : 1 },
        itemStyle: { opacity: faded ? FADED : 1 },
        emphasis: { disabled: true },
        markArea: index === 0 && bands.length ? { silent: true, data: bands } : undefined,
      };
    }),
  };
}

/** FR-402: lap times of the selected drivers as a scatter plot. */
export function buildLapsOption(data: Laps, tokens: ChartTokens): EChartOption {
  const { axisText, tooltip, line } = axisBits(tokens);
  const bands = bandAreas(neutralisationBands(data.neutralisations), tokens);
  const dashed = dashedDrivers(data.drivers);
  return {
    animation: false,
    textStyle: { color: tokens.fg },
    grid: { left: 8, right: 20, top: 16, bottom: 8, containLabel: true },
    tooltip: {
      ...tooltip,
      trigger: "item",
      formatter: (p: { seriesName: string; value: [number, number] }) =>
        `${p.seriesName}, lap ${p.value[0]}: ${formatLapTime(p.value[1]) ?? ""}`,
    },
    dataZoom: [
      { type: "inside", xAxisIndex: 0, filterMode: "none" },
      { type: "inside", yAxisIndex: 0, filterMode: "none" },
    ],
    xAxis: {
      type: "value",
      name: "Lap",
      nameLocation: "middle",
      nameGap: 28,
      nameTextStyle: axisText,
      scale: true,
      minInterval: 1,
      axisLine: line,
      axisLabel: axisText,
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      name: "Lap time",
      nameTextStyle: axisText,
      scale: true,
      axisLabel: { ...axisText, formatter: (v: number) => formatLapTime(v) ?? "" },
      splitLine: { lineStyle: { color: tokens.line } },
    },
    series: data.drivers.map((d, index) => ({
      name: d.code,
      type: "scatter",
      color: teamColor(d.color_hex, tokens.muted),
      // Teammates share a colour: the second driver gets a different marker.
      symbol: dashed.has(d.code) ? "diamond" : "circle",
      symbolSize: 7,
      data: d.lap_numbers.flatMap((lap, i) => {
        const ms = d.duration_ms[i];
        return lap != null && ms != null ? [[lap, ms]] : [];
      }),
      markArea: index === 0 && bands.length ? { silent: true, data: bands } : undefined,
    })),
  };
}

/** FR-406: air and track temperature over the session. */
export function buildWeatherOption(data: Weather, tokens: ChartTokens): EChartOption {
  const { axisText, tooltip, line } = axisBits(tokens);
  const times = data.samples.map((s) => new Date(s.ts).toISOString().slice(11, 16));
  return {
    animation: false,
    textStyle: { color: tokens.fg },
    color: [tokens.palette[0] ?? tokens.accent, tokens.palette[1] ?? tokens.muted],
    grid: { left: 8, right: 20, top: 36, bottom: 8, containLabel: true },
    legend: { top: 0, textStyle: { color: tokens.fg } },
    tooltip: { ...tooltip, trigger: "axis" },
    dataZoom: zoom(),
    xAxis: { type: "category", data: times, axisLine: line, axisLabel: axisText, boundaryGap: false },
    yAxis: {
      type: "value",
      name: "°C",
      nameTextStyle: axisText,
      scale: true,
      axisLabel: axisText,
      splitLine: { lineStyle: { color: tokens.line } },
    },
    series: [
      { name: "Air", type: "line", symbol: "none", data: data.samples.map((s) => s.air_temperature) },
      { name: "Track", type: "line", symbol: "none", lineStyle: { type: "dashed" }, data: data.samples.map((s) => s.track_temperature) },
    ],
  };
}

