"use client";

import { useQuery } from "@tanstack/react-query";
import { AnalyticsError, analyticsKey, type AnalyticsRef } from "./data";

const FIVE_MINUTES = 5 * 60_000;

/** One cached request per session and view; a 404 is a final answer, not worth a retry. */
export function useAnalytics<T>(kind: string, ref: AnalyticsRef, fn: () => Promise<T>, ...extra: (string | boolean)[]) {
  return useQuery({
    queryKey: analyticsKey(kind, ref, ...extra),
    queryFn: fn,
    staleTime: FIVE_MINUTES,
    retry: (count, err) => !(err instanceof AnalyticsError && err.status === 404) && count < 1,
  });
}
