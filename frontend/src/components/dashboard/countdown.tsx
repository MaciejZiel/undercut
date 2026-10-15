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
  if (!parts) return <p className="display text-4xl">Lights out</p>;
  const cells: [string, number][] = [
    ["days", parts.days],
    ["hours", parts.hours],
    ["min", parts.minutes],
    ["sec", parts.seconds],
  ];
  return (
    <div role="timer" aria-label={`${parts.days} days, ${parts.hours} hours and ${parts.minutes} minutes to go`}>
      <dl aria-hidden="true" className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
        {cells.map(([label, value]) => (
          <div key={label} className="flex items-baseline gap-1.5">
            <dd className="numeral text-5xl sm:text-6xl">{String(value).padStart(2, "0")}</dd>
            <dt className="label">{label}</dt>
          </div>
        ))}
      </dl>
    </div>
  );
}
