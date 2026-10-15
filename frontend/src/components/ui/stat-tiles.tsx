import type { ReactNode } from "react";
import { orDash } from "./value";

export type Stat = { label: string; value: ReactNode | null; hint?: string };

/** A row of figures under a heavy rule, 4 across on desktop and 2 on mobile. A null value is a dash, never 0. */
export function StatTiles({ stats, label = "Statistics" }: { stats: Stat[]; label?: string }) {
  return (
    <dl aria-label={label} className="mb-10 grid grid-cols-2 gap-x-8 border-t-2 border-fg lg:grid-cols-4">
      {stats.map((s) => (
        <div key={s.label} className="border-b border-line py-4">
          <dt className="label">{s.label}</dt>
          <dd className="numeral mt-1 text-4xl">{orDash(s.value, s.hint)}</dd>
        </div>
      ))}
    </dl>
  );
}
