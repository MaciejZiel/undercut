import type { ReactNode } from "react";
import { orDash } from "./value";

export type Stat = { label: string; value: ReactNode | null; hint?: string };

/** 4 columns on desktop, 2 on mobile. A null value shows an em dash, never 0. */
export function StatTiles({ stats, label = "Statistics" }: { stats: Stat[]; label?: string }) {
  return (
    <dl aria-label={label} className="mb-8 grid grid-cols-2 gap-3 lg:grid-cols-4">
      {stats.map((s) => (
        <div key={s.label} className="rounded-lg border border-line bg-surface p-4">
          <dt className="text-xs font-bold uppercase tracking-wide text-muted">{s.label}</dt>
          <dd className="timing mt-1 text-2xl font-extrabold tracking-tight">{orDash(s.value, s.hint)}</dd>
        </div>
      ))}
    </dl>
  );
}
