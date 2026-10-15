import type { ReactNode } from "react";
import { orDash } from "./value";

export type Stat = { label: string; value: ReactNode | null; hint?: string };

/** A line of figures between two hairlines: big tabular numbers, a caption under each. A null value is a dash, never 0. */
export function StatTiles({ stats, label = "Statistics" }: { stats: Stat[]; label?: string }) {
  return (
    <dl aria-label={label} className="mb-10 grid grid-cols-2 gap-x-10 gap-y-6 border-b border-line pb-6 sm:grid-cols-3 lg:flex lg:flex-wrap">
      {stats.map((s) => (
        <div key={s.label} className="flex min-w-0 flex-col-reverse justify-end">
          <dt className="mt-1 text-[0.8125rem] font-semibold text-muted">{s.label}</dt>
          <dd className="numeral text-[1.75rem] sm:text-3xl">{orDash(s.value, s.hint)}</dd>
        </div>
      ))}
    </dl>
  );
}
