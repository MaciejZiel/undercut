"use client";

import { useState } from "react";
import type { SessionType } from "@/lib/api/queries";
import type { AnalyticsRef } from "./data";
import { LapsView } from "./laps-view";
import { PitStopsView } from "./pit-stops-view";
import { PositionsView } from "./positions-view";
import { RaceControlView } from "./race-control-view";
import { StintsView } from "./stints-view";
import { WeatherView } from "./weather-view";

export const ANALYSIS_SECTIONS = [
  { key: "positions", label: "Positions" },
  { key: "laps", label: "Lap times" },
  { key: "pits", label: "Pit stops" },
  { key: "weather", label: "Weather" },
  { key: "control", label: "Race control" },
] as const;

type SectionKey = (typeof ANALYSIS_SECTIONS)[number]["key"];

/** Body of the Analysis and Strategy tabs. Data is fetched in the browser, per session, and cached. */
export function AnalyticsPanel({
  view,
  year,
  round,
  session,
}: {
  view: "analysis" | "strategy";
  year: number;
  round: number;
  session: SessionType;
}) {
  const refs: AnalyticsRef = { year, round, session };
  const [section, setSection] = useState<SectionKey>("positions");

  if (view === "strategy") return <StintsView refs={refs} />;

  return (
    <div>
      <div role="group" aria-label="Analysis view" className="mb-4 flex flex-wrap gap-1">
        {ANALYSIS_SECTIONS.map((s) => (
          <button
            key={s.key}
            type="button"
            aria-pressed={section === s.key}
            onClick={() => setSection(s.key)}
            className={`t-fast rounded-md border px-3 py-1.5 text-sm font-semibold ${
              section === s.key ? "border-accent bg-accent-soft text-accent" : "border-line text-muted hover:text-fg"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>
      {section === "positions" && <PositionsView refs={refs} />}
      {section === "laps" && <LapsView refs={refs} />}
      {section === "pits" && <PitStopsView refs={refs} />}
      {section === "weather" && <WeatherView refs={refs} />}
      {section === "control" && <RaceControlView refs={refs} />}
    </div>
  );
}
