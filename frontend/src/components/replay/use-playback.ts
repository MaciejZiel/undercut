"use client";

import { useSyncExternalStore } from "react";
import type { PlaybackController, PlaybackSnapshot } from "@/lib/replay/controller";

/**
 * Subscribe to one primitive derived from the controller snapshot. The component re-renders
 * only when the selected value changes, so a table keyed on the frame index renders once per
 * frame step instead of once per animation frame.
 */
export function usePlayback<T extends string | number | boolean | null>(
  controller: PlaybackController,
  select: (snapshot: PlaybackSnapshot) => T,
): T {
  const get = () => select(controller.getSnapshot());
  return useSyncExternalStore(controller.subscribe, get, get);
}
