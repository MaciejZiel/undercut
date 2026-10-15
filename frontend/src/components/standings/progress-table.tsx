import type { Progress } from "@/lib/api/queries";
import { formatPoints } from "@/lib/format";
import { DataTable, RowTh, Td, Th, Tr } from "@/components/ui/data-table";
import { Dash } from "@/components/ui/value";
import { seriesValues, type ProgressMetric } from "./progress-option";

/** Text alternative of the chart (NFR-403): one row per entity, one column per round. */
export function ProgressTable({
  data,
  selected,
  metric,
  caption,
}: {
  data: Progress;
  selected: string[];
  metric: ProgressMetric;
  caption: string;
}) {
  const chosen = new Set(selected);
  const rows = data.series.filter((s) => chosen.has(s.entity.slug));
  return (
    <DataTable caption={caption} minWidth={`${Math.max(24, 9 + data.rounds.length * 3.5)}rem`}>
      <thead>
        <tr>
          <Th>{metric === "points" ? "Cumulative points" : "Position"}</Th>
          {data.rounds.map((r) => (
            <Th key={r} align="right">
              R{r}
            </Th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((s) => (
          <Tr key={s.entity.slug}>
            <RowTh className="whitespace-nowrap font-semibold">{s.entity.name}</RowTh>
            {seriesValues(s, metric).map((v, i) => (
              <Td key={data.rounds[i] ?? i} align="right" className="timing">
                {v === null || v === undefined ? <Dash /> : metric === "points" ? formatPoints(v) : v}
              </Td>
            ))}
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}
