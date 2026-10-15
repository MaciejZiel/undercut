"use client";

import { useSyncExternalStore } from "react";
import { useAuth } from "@/lib/auth/auth-context";
import { browserTimeZone } from "@/lib/auth/settings";
import { safeZone } from "./time";

const noop = () => () => {};

/**
 * The viewer's time zone: the saved account setting when signed in, otherwise the browser's.
 * The server render and hydration use UTC (the browser zone is unknown there), then it switches.
 */
export function useViewerZone(): string {
  const { user } = useAuth();
  const browser = useSyncExternalStore(noop, browserTimeZone, () => null);
  return safeZone(user?.timezone) ?? safeZone(browser) ?? "UTC";
}
