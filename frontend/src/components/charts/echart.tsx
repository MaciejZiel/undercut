"use client";

import { useEffect, useRef, useState } from "react";
import type { EChartsCoreOption, EChartsType } from "echarts/core";
import { readChartTokens, type ChartTokens } from "./tokens";

export type EChartOption = EChartsCoreOption;

/**
 * Thin ECharts wrapper: canvas renderer, a tree-shaken set of chart types, theme tokens read
 * from CSS variables, a ResizeObserver, and full cleanup on unmount. echarts itself is loaded
 * with a dynamic import, so pages that do not render a chart never download it.
 *
 * `option` may be a function of the current theme tokens; it is re-evaluated when the theme
 * changes. Base text, axis and tooltip styling should come from `tokens` inside that function.
 */
export function EChart({
  option,
  label,
  height = 360,
  className = "",
}: {
  option: EChartOption | ((tokens: ChartTokens) => EChartOption);
  /** Accessible name of the chart; point to a table alternative next to it. */
  label: string;
  height?: number | string;
  className?: string;
}) {
  const host = useRef<HTMLDivElement>(null);
  const chart = useRef<EChartsType | null>(null);
  const [ready, setReady] = useState(false);
  const [themeTick, setThemeTick] = useState(0);
  const [failed, setFailed] = useState(false);

  // Create the instance once.
  useEffect(() => {
    const el = host.current;
    if (!el) return;
    let disposed = false;
    let observer: ResizeObserver | undefined;
    import("./echarts-setup")
      .then(({ echarts }) => {
        if (disposed) return;
        chart.current = echarts.init(el, undefined, { renderer: "canvas" });
        if (typeof ResizeObserver !== "undefined") {
          observer = new ResizeObserver(() => chart.current?.resize());
          observer.observe(el);
        }
        setReady(true);
      })
      .catch(() => {
        if (!disposed) setFailed(true);
      });
    return () => {
      disposed = true;
      observer?.disconnect();
      chart.current?.dispose();
      chart.current = null;
      setReady(false);
    };
  }, []);

  // Re-render when the theme flips (explicit toggle or the system preference).
  useEffect(() => {
    const bump = () => setThemeTick((n) => n + 1);
    const mo = new MutationObserver(bump);
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    const mq = typeof window.matchMedia === "function" ? window.matchMedia("(prefers-color-scheme: dark)") : null;
    mq?.addEventListener("change", bump);
    return () => {
      mo.disconnect();
      mq?.removeEventListener("change", bump);
    };
  }, []);

  useEffect(() => {
    const c = chart.current;
    if (!ready || !c) return;
    const resolved = typeof option === "function" ? option(readChartTokens()) : option;
    c.setOption(resolved, { notMerge: true });
  }, [option, ready, themeTick]);

  return (
    <div className={`relative w-full ${className}`} style={{ height }}>
      <div ref={host} role="img" aria-label={label} className="size-full" />
      {!ready && !failed && <div className="skeleton absolute inset-0 rounded-md" aria-hidden="true" />}
      {failed && (
        <p className="absolute inset-0 p-4 text-sm text-muted">
          The chart could not be loaded. Use the table view instead.
        </p>
      )}
    </div>
  );
}
