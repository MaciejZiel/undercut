"use client";

import { useId, useState, type ReactNode } from "react";

/** Drivers / Constructors switch for the championship panel. Both tables are rendered by the server; this only picks one. */
export function StandingsSwitch({ drivers, constructors, season, afterRound }: { drivers: ReactNode; constructors: ReactNode; season?: number | null; afterRound?: number | null }) {
  const [kind, setKind] = useState<"drivers" | "constructors">("drivers");
  const id = useId();
  return (
    <div>
      <div className="flex items-end justify-between gap-4 border-b border-line">
        <div role="group" aria-label="Championship" className="flex gap-6">
          {(["drivers", "constructors"] as const).map((k) => (
            <button
              key={k}
              type="button"
              aria-pressed={kind === k}
              aria-controls={`${id}-panel`}
              onClick={() => setKind(k)}
              className={`t-fast -mb-px min-h-11 border-b-[3px] px-0.5 text-sm font-bold ${
                kind === k ? "border-accent text-accent" : "border-transparent text-muted hover:text-accent"
              }`}
            >
              {k === "drivers" ? "Drivers" : "Constructors"}
            </button>
          ))}
        </div>
        {afterRound ? <span className="pb-3 text-xs text-muted">After round {afterRound}</span> : null}
      </div>
      <div id={`${id}-panel`} className="pt-4">
        {kind === "drivers" ? drivers : constructors}
      </div>
      {season ? <span className="sr-only">Season {season}</span> : null}
    </div>
  );
}
