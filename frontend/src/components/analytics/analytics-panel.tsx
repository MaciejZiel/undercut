"use client";

import type { AnalyticsSessionType } from "@/lib/api/queries";
import type { AnalyticsRef } from "./data";
import { LapsView } from "./laps-view";
import { PitStopsView } from "./pit-stops-view";
import { PositionsView } from "./positions-view";
import { RaceControlView } from "./race-control-view";
import { StintsView } from "./stints-view";
import { WeatherView } from "./weather-view";

export type AnalyticsViewKey = "positions" | "laps" | "tyres" | "pits" | "weather" | "control";

/** Body of one analytics view of the round page, picked by the URL. Data is fetched in the browser, per session, and cached. */
export function AnalyticsPanel({
  view,
  year,
  round,
  session,
}: {
  view: AnalyticsViewKey;
  year: number;
  round: number;
  session: AnalyticsSessionType;
}) {
  const refs: AnalyticsRef = { year, round, session };
  switch (view) {
    case "positions":
      return <PositionsView refs={refs} />;
    case "laps":
      return <LapsView refs={refs} />;
    case "tyres":
      return <StintsView refs={refs} />;
    case "pits":
      return <PitStopsView refs={refs} />;
    case "weather":
      return <WeatherView refs={refs} />;
    case "control":
      return <RaceControlView refs={refs} />;
  }
}
