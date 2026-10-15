"use client";

import { useState } from "react";
import { fetchRaceControl, type AnalyticsRef, type RaceControl } from "./data";
import { RequestState } from "./chart-frame";
import { useAnalytics } from "./hooks";

export function RaceControlView({ refs }: { refs: AnalyticsRef }) {
  const query = useAnalytics("race-control", refs, () => fetchRaceControl(refs));
  return (
    <RequestState query={query} isEmpty={(d) => d.messages.length === 0} emptyTitle="No race control messages">
      {(data) => <MessageList data={data} />}
    </RequestState>
  );
}

export function filterMessages(messages: RaceControl["messages"], category: string | null) {
  return category ? messages.filter((m) => m.category === category) : messages;
}

function MessageList({ data }: { data: RaceControl }) {
  const [category, setCategory] = useState<string | null>(null);
  const shown = filterMessages(data.messages, category);
  return (
    <section aria-labelledby="rc-h" className="rounded-xl bg-surface p-3">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h3 id="rc-h" className="mr-auto text-base font-bold">
          Race control messages
        </h3>
        <label className="text-sm font-semibold">
          <span className="mr-2 text-muted">Category</span>
          <select
            value={category ?? ""}
            onChange={(e) => setCategory(e.target.value || null)}
            className="rounded-md border border-line-strong bg-bg px-2 py-1"
          >
            <option value="">All</option>
            {data.categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
      </div>
      <ol className="max-h-[32rem] divide-y divide-line overflow-auto text-sm">
        {shown.map((m, i) => (
          <li key={`${m.ts}-${i}`} className="flex flex-wrap gap-x-3 py-2">
            <span className="timing w-14 shrink-0 font-bold text-muted">{m.lap_number != null ? `Lap ${m.lap_number}` : new Date(m.ts).toISOString().slice(11, 16)}</span>
            {m.category && <span className="rounded bg-surface-2 px-1.5 text-xs font-bold">{m.category}{m.flag ? ` · ${m.flag}` : ""}</span>}
            <span className="min-w-0 flex-1">{m.message}</span>
          </li>
        ))}
      </ol>
      <p className="mt-2 text-xs text-muted">Data: OpenF1</p>
    </section>
  );
}
