"use client";

import { useSyncExternalStore } from "react";
import { countdownParts } from "./countdown-parts";

function subscribe(onChange: () => void) {
  const id = window.setInterval(onChange, 1000);
  return () => window.clearInterval(id);
}
const snapshot = () => Math.floor(Date.now() / 1000);
const serverSnapshot = () => null;

/**
 * Live countdown. The server render and the first client render show a static
 * label (no clock), so hydration never mismatches; the timer starts afterwards.
 */
export function Countdown({ target }: { target: string }) {
  const nowSec = useSyncExternalStore(subscribe, snapshot, serverSnapshot);
  const targetMs = Date.parse(target);
  if (nowSec === null || Number.isNaN(targetMs)) {
    return <p className="text-sm text-muted">Countdown loading</p>;
  }
  const parts = countdownParts(targetMs, nowSec * 1000);
  if (!parts) return <p className="font-bold">Lights out</p>;
  const cells: [string, number][] = [
    ["days", parts.days],
    ["hrs", parts.hours],
    ["min", parts.minutes],
    ["sec", parts.seconds],
  ];
  return (
    <div role="timer" aria-label={`${parts.days} days, ${parts.hours} hours and ${parts.minutes} minutes to go`}>
      <dl aria-hidden="true" className="timing flex gap-3">
        {cells.map(([label, value]) => (
          <div key={label} className="min-w-12 rounded-md bg-surface-2 px-2 py-1.5 text-center">
            <dd className="text-2xl font-extrabold leading-none">{String(value).padStart(2, "0")}</dd>
            <dt className="mt-1 text-[0.65rem] font-bold uppercase tracking-wide text-muted">{label}</dt>
          </div>
        ))}
      </dl>
    </div>
  );
}
