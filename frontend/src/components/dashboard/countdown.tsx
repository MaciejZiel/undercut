"use client";

import { countdownParts } from "./countdown-parts";
import { useNow } from "./use-now";

/** Two digits, each in a box of one width, so the clock does not shift when a figure changes in any browser or font. */
function Digits({ value }: { value: number }) {
  return (
    <>
      {String(value)
        .padStart(2, "0")
        .split("")
        .map((c, i) => (
          <span key={i} className="inline-block w-[0.64em] whitespace-nowrap text-center">
            {c}
          </span>
        ))}
    </>
  );
}

/**
 * Live countdown. The server render and the first client render show a static
 * label (no clock), so hydration never mismatches; the timer starts afterwards.
 * `clock` is the big face of the home page: 10 : 03 : 34 : 12 with the unit under each pair.
 */
export function Countdown({ target, clock = false }: { target: string; clock?: boolean }) {
  const now = useNow(1000);
  const targetMs = Date.parse(target);
  if (now === null || Number.isNaN(targetMs)) {
    return <p className="text-sm text-muted">Countdown loading</p>;
  }
  const parts = countdownParts(targetMs, now);
  if (!parts) return <p className="display text-3xl">Lights out</p>;
  const cells: [string, number][] = [
    ["days", parts.days],
    ["hrs", parts.hours],
    ["min", parts.minutes],
    ["sec", parts.seconds],
  ];
  const label = `${parts.days} days, ${parts.hours} hours and ${parts.minutes} minutes to go`;
  if (clock) {
    return (
      <div role="timer" aria-label={label}>
        <dl aria-hidden="true" className="flex items-start gap-x-2">
          {cells.map(([unit, value], i) => (
            <div key={unit} className="flex shrink-0 items-start gap-x-2">
              <div className="shrink-0">
                <dd className="numeral whitespace-nowrap text-[2.5rem] sm:text-[2.75rem]"><Digits value={value} /></dd>
                <dt className="eyebrow mt-1.5">{unit}</dt>
              </div>
              {i < cells.length - 1 && <span className="numeral text-[2.5rem] text-line-strong sm:text-[2.75rem]">:</span>}
            </div>
          ))}
        </dl>
      </div>
    );
  }
  return (
    <div role="timer" aria-label={label}>
      <dl aria-hidden="true" className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        {cells.map(([unit, value]) => (
          <div key={unit} className="flex items-baseline gap-1.5">
            <dd className="numeral whitespace-nowrap text-[1.75rem] sm:text-3xl"><Digits value={value} /></dd>
            <dt className="text-sm font-semibold text-muted">{unit}</dt>
          </div>
        ))}
      </dl>
    </div>
  );
}
