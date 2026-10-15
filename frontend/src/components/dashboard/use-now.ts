"use client";

import { useSyncExternalStore } from "react";

/**
 * The current time in milliseconds, ticking every `intervalMs`. The server render and the first client
 * render get null (there is no shared clock), so nothing time-dependent can mismatch on hydration.
 */
export function useNow(intervalMs = 1000): number | null {
  return useSyncExternalStore(
    (onChange) => {
      const id = window.setInterval(onChange, intervalMs);
      return () => window.clearInterval(id);
    },
    () => Math.floor(Date.now() / intervalMs) * intervalMs,
    () => null,
  );
}
