"use client";

import { useId, useState, type ReactNode } from "react";

/** Drivers / Constructors switch for the championship panel. Both tables are rendered by the server; this only picks one. */
export function StandingsSwitch({ drivers, constructors, season }: { drivers: ReactNode; constructors: ReactNode; season?: number | null }) {
  const [kind, setKind] = useState<"drivers" | "constructors">("drivers");
  const id = useId();
  return (
    <div>
      <div className="mb-3 flex items-end justify-between gap-4">
        <div role="group" aria-label="Championship" className="flex gap-6">
          {(["drivers", "constructors"] as const).map((k) => (
            <button
              key={k}
              type="button"
              aria-pressed={kind === k}
              aria-controls={`${id}-panel`}
              onClick={() => setKind(k)}
              className={`t-fast min-h-9 border-b-2 text-sm font-bold ${
                kind === k ? "border-accent text-fg" : "border-transparent text-muted hover:text-fg"
              }`}
            >
              {k === "drivers" ? "Drivers" : "Constructors"}
            </button>
          ))}
        </div>
      </div>
      <div id={`${id}-panel`} key={kind} className="fade-in">
        {kind === "drivers" ? drivers : constructors}
      </div>
      {season ? <span className="sr-only">Season {season}</span> : null}
    </div>
  );
}
