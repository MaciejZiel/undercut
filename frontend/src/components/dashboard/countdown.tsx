"use client";

import { countdownParts } from "./countdown-parts";
import { useNow } from "./use-now";

/**
 * Live countdown. The server render and the first client render show a static
 * label (no clock), so hydration never mismatches; the timer starts afterwards.
 */
export function Countdown({ target }: { target: string }) {
  const now = useNow(1000);
  const targetMs = Date.parse(target);
  if (now === null || Number.isNaN(targetMs)) {
    return <p className="text-sm text-muted">Countdown loading</p>;
  }
  const parts = countdownParts(targetMs, now);
  if (!parts) return <p className="display text-3xl">Lights out</p>;
  const cells: [string, number][] = [
    ["days", parts.days],
    ["hours", parts.hours],
    ["min", parts.minutes],
    ["sec", parts.seconds],
  ];
  return (
    <div role="timer" aria-label={`${parts.days} days, ${parts.hours} hours and ${parts.minutes} minutes to go`}>
      <dl aria-hidden="true" className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        {cells.map(([label, value]) => (
          <div key={label} className="flex items-baseline gap-1.5">
            <dd className="numeral text-[1.75rem] sm:text-3xl">{String(value).padStart(2, "0")}</dd>
            <dt className="text-xs font-semibold text-muted">{label}</dt>
          </div>
        ))}
      </dl>
    </div>
  );
}
