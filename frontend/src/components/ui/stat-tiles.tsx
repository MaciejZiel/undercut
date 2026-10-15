import type { ReactNode } from "react";
import { orDash } from "./value";

export type Stat = { label: string; value: ReactNode | null; hint?: string };

/** A row of figures under a heavy rule, 4 across on desktop and 2 on mobile. A null value is a dash, never 0. */
export function StatTiles({ stats, label = "Statistics" }: { stats: Stat[]; label?: string }) {
  return (
    <dl aria-label={label} className="mb-10 grid grid-cols-2 overflow-hidden rounded-xl bg-surface lg:grid-cols-4">
      {stats.map((s) => (
        <div key={s.label} className="border-b border-line px-5 py-4 last:border-b-0 sm:px-6 sm:py-5 lg:border-b-0 lg:border-l lg:first:border-l-0">
          <dt className="label">{s.label}</dt>
          <dd className="numeral mt-1.5 text-4xl">{orDash(s.value, s.hint)}</dd>
        </div>
      ))}
    </dl>
  );
}
