"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { createApiClient } from "@/lib/api/client";
import type { Progress, StandingsKind } from "@/lib/api/queries";
import { EChart } from "@/components/charts/echart";
import { readChartTokens, type ChartTokens } from "@/components/charts/tokens";
import { ErrorState } from "@/components/states/error-state";
import { EmptyState } from "@/components/states/empty-state";
import {
  buildProgressOption,
  defaultSelection,
  lineLook,
  toggleSelection,
  type ProgressMetric,
} from "./progress-option";
import { ProgressTable } from "./progress-table";

/** Candidates offered as toggles; the chart starts with the top five of them. */
const POOL = 40;

async function fetchProgress(kind: StandingsKind, season: number): Promise<Progress> {
  const api = createApiClient(window.location.origin);
  const query = { season, top: POOL };
  const { data, error } =
    kind === "drivers"
      ? await api.GET("/api/v1/standings/drivers/progress/", { params: { query } })
      : await api.GET("/api/v1/standings/constructors/progress/", { params: { query } });
  if (error || !data) throw new Error("Progress request failed");
  return data;
}

const toggleBase =
  "t-fast rounded-sm border px-3 py-1.5 text-sm font-semibold";

export function PointsChart({ kind, season }: { kind: StandingsKind; season: number }) {
  const query = useQuery({
    queryKey: ["standings-progress", kind, season],
    queryFn: () => fetchProgress(kind, season),
  });

  if (query.isPending) {
    return <div className="skeleton h-[22rem] w-full rounded-sm" role="status" aria-label="Loading chart" />;
  }
  if (query.isError) {
    return (
      <ErrorState
        title="Could not load the points chart"
        description="The standings table above is still available."
        onRetry={() => void query.refetch()}
      />
    );
  }
  if (query.data.series.length === 0 || query.data.rounds.length === 0) {
    return <EmptyState title="No progression yet" description="Points appear here after the first round of the season." />;
  }
  return <ChartPanel key={`${kind}-${season}`} data={query.data} kind={kind} season={season} />;
}

function ChartPanel({ data, kind, season }: { data: Progress; kind: StandingsKind; season: number }) {
  const [selected, setSelected] = useState(() => defaultSelection(data));
  const [metric, setMetric] = useState<ProgressMetric>("points");
  const [asTable, setAsTable] = useState(false);

  const option = useMemo(
    () => (tokens: ChartTokens) => buildProgressOption(data, selected, metric, tokens),
    [data, selected, metric],
  );
  const noun = kind === "drivers" ? "drivers" : "constructors";
  const label = `${season} ${noun} championship ${metric === "points" ? "cumulative points" : "position"} per round`;
  const isDefault = selected.join() === defaultSelection(data).join();

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div role="group" aria-label="Chart metric" className="flex gap-1">
          {(["points", "position"] as const).map((m) => (
            <button
              key={m}
              type="button"
              aria-pressed={metric === m}
              onClick={() => setMetric(m)}
              className={`${toggleBase} ${metric === m ? "border-accent bg-accent-soft text-accent" : "border-line text-muted hover:text-fg"}`}
            >
              {m === "points" ? "Points" : "Position"}
            </button>
          ))}
        </div>
        <button
          type="button"
          aria-pressed={asTable}
          onClick={() => setAsTable((v) => !v)}
          className={`${toggleBase} ml-auto border-line hover:text-accent`}
        >
          {asTable ? "Show as chart" : "Show as table"}
        </button>
      </div>

      <fieldset className="mb-4">
        <legend className="mb-2 text-sm font-bold text-muted">
          Showing {selected.length} of {data.series.length}
        </legend>
        <ul className="flex flex-wrap gap-2">
          {data.series.map((s, index) => {
            const on = selected.includes(s.entity.slug);
            return (
              <li key={s.entity.slug}>
                <button
                  type="button"
                  aria-pressed={on}
                  onClick={() => setSelected((cur) => toggleSelection(data, cur, s.entity.slug))}
                  className={`${toggleBase} inline-flex items-center gap-2 ${on ? "border-line bg-surface text-fg" : "border-transparent bg-surface-2 text-muted hover:text-fg"}`}
                >
                  <ChipMark color={on ? lineLook(data, index, readChartTokens()) : null} />
                  {s.entity.code ?? s.entity.name}
                  <span className="sr-only">{on ? ", shown. Activate to hide." : ", hidden. Activate to show."}</span>
                </button>
              </li>
            );
          })}
        </ul>
        {!isDefault && (
          <button
            type="button"
            onClick={() => setSelected(defaultSelection(data))}
            className="t-fast mt-2 text-sm font-semibold text-muted hover:text-fg"
          >
            Reset to top 5
          </button>
        )}
      </fieldset>

      {selected.length === 0 ? (
        <EmptyState title="No lines selected" description="Pick at least one entry above to draw the chart." />
      ) : asTable ? (
        <ProgressTable data={data} selected={selected} metric={metric} caption={label} />
      ) : (
        <div className="py-3">
          <EChart option={option} label={label} height={360} />
        </div>
      )}
    </div>
  );
}

/** The legend mark of a line: solid or dashed in the team colour, grey when the line is hidden. */
function ChipMark({ color }: { color: { color: string; dashed: boolean } | null }) {
  return (
    <span
      aria-hidden="true"
      className="inline-block h-0 w-5 border-t-[3px]"
      style={{
        borderTopColor: color?.color ?? "var(--fg-muted)",
        borderTopStyle: color?.dashed ? "dashed" : "solid",
        opacity: color ? 1 : 0.4,
      }}
    />
  );
}
