"use client";

import { useEffect, useState, type ReactNode } from "react";
import { EChart, type EChartOption } from "@/components/charts/echart";
import type { ChartTokens } from "@/components/charts/tokens";
import { ErrorState } from "@/components/states/error-state";
import { EmptyState } from "@/components/states/empty-state";
import { AnalyticsError } from "./data";

const btn = "t-fast rounded-sm border border-line px-3 py-1.5 text-sm font-semibold text-muted hover:text-fg";

/**
 * Shared chrome of every analytics chart: title, "Show as table" and "Full screen" buttons, a
 * source caption and, on small screens, the hint to rotate the phone. The legend is a slot
 * (`legend`) shown to the right of the chart on desktop and below it on mobile.
 */
export function ChartFrame({
  title,
  chart,
  table,
  legend,
  source = "OpenF1",
  controls,
  zoomable = true,
}: {
  title: string;
  chart: ReactNode;
  table: ReactNode;
  legend?: ReactNode;
  source?: string;
  controls?: ReactNode;
  zoomable?: boolean;
}) {
  const [asTable, setAsTable] = useState(false);
  const [full, setFull] = useState(false);

  useEffect(() => {
    if (!full) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setFull(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [full]);

  return (
    <figure
      className={
        full
          ? "fixed inset-0 z-50 flex flex-col overflow-auto bg-bg p-4"
          : "rounded-sm border border-line bg-surface p-3"
      }
      aria-label={title}
    >
      <figcaption className="mb-3 flex flex-wrap items-center gap-2">
        <h3 className="mr-auto text-base font-extrabold tracking-tight">{title}</h3>
        {controls}
        <button type="button" aria-pressed={asTable} onClick={() => setAsTable((v) => !v)} className={btn}>
          {asTable ? "Show as chart" : "Show as table"}
        </button>
        <button type="button" aria-pressed={full} onClick={() => setFull((v) => !v)} className={btn}>
          {full ? "Exit full screen" : "Full screen"}
        </button>
      </figcaption>
      {asTable ? (
        <div className={full ? "min-h-0 flex-1 overflow-auto" : ""}>{table}</div>
      ) : (
        <div className={`flex min-h-0 flex-col gap-3 lg:flex-row ${full ? "flex-1" : ""}`}>
          <div className={`min-w-0 lg:flex-1 ${full ? "h-[calc(100dvh-9rem)]" : "h-[320px] md:h-[420px]"}`}>{chart}</div>
          {legend && <div className="lg:w-44 lg:shrink-0 lg:overflow-y-auto">{legend}</div>}
        </div>
      )}
      <p className="mt-2 flex flex-wrap gap-x-4 text-xs text-muted">
        <span>Data: {source}</span>
        {!asTable && zoomable && (
          <>
            <span className="md:hidden">Pinch to zoom. Rotate your phone to see more.</span>
            <span className="hidden md:inline">Scroll or pinch to zoom.</span>
          </>
        )}
      </p>
    </figure>
  );
}

/** EChart that first registers the extra chart types the analytics views need. */
export function AnalyticsChart({
  option,
  label,
}: {
  option: EChartOption | ((tokens: ChartTokens) => EChartOption);
  label: string;
}) {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let alive = true;
    import("./setup")
      .catch(() => undefined)
      .then(() => {
        if (alive) setReady(true);
      });
    return () => {
      alive = false;
    };
  }, []);
  if (!ready) return <div className="skeleton size-full rounded-sm" aria-hidden="true" />;
  return <EChart option={option} label={label} height="100%" />;
}

export function ChartSkeleton({ label = "Loading chart" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="skeleton h-[320px] w-full rounded-sm md:h-[420px]">
      <span className="sr-only">{label}…</span>
    </div>
  );
}

/** Loading, error and empty states for one analytics request. */
export function RequestState<T>({
  query,
  isEmpty,
  emptyTitle,
  emptyDescription,
  children,
}: {
  query: { isPending: boolean; isError: boolean; error: unknown; data: T | undefined; refetch: () => unknown };
  isEmpty: (data: T) => boolean;
  emptyTitle: string;
  emptyDescription?: string;
  children: (data: T) => ReactNode;
}) {
  if (query.isPending) return <ChartSkeleton />;
  if (query.isError) {
    const err = query.error;
    if (err instanceof AnalyticsError && err.status === 404) {
      return (
        <EmptyState
          title={err.analyticsAvailable === false ? "No detailed analytics for this season" : "No data for this session"}
          description={
            err.analyticsAvailable === false
              ? "Detailed analytics are available from the 2023 season."
              : "The data appears here once the session has been processed."
          }
        />
      );
    }
    return (
      <ErrorState
        title="Could not load the analytics"
        description="The results above are still available."
        onRetry={() => void query.refetch()}
      />
    );
  }
  const data = query.data as T;
  if (isEmpty(data)) return <EmptyState title={emptyTitle} description={emptyDescription} />;
  return <>{children(data)}</>;
}
