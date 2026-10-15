"use client";

import { useQuery } from "@tanstack/react-query";
import { createApiClient } from "@/lib/api/client";
import type { ReplayDoc } from "./types";

export type ReplaySession = "RACE" | "SPRINT";

export class ReplayLoadError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ReplayLoadError";
  }
}

export const REPLAY_STEP = 5;
/** The payload of a finished session never changes (about 500 KB): keep it for the whole visit. */
export const REPLAY_STALE_MS = 60 * 60 * 1000;

export const replayKey = (year: number, round: number, session: ReplaySession, step = REPLAY_STEP) =>
  ["replay", year, round, session, step] as const;

export async function fetchReplay(
  year: number,
  round: number,
  session: ReplaySession,
  step = REPLAY_STEP,
  baseUrl?: string,
): Promise<ReplayDoc> {
  const { data, response } = await createApiClient(baseUrl).GET("/api/v1/rounds/{year}/{round}/replay/", {
    params: { path: { year, round }, query: { session, step } },
  });
  if (!data) throw new ReplayLoadError(response.status, `Replay request failed (${response.status})`);
  return data as unknown as ReplayDoc;
}

export function useReplay(year: number, round: number, session: ReplaySession, enabled = true) {
  return useQuery({
    queryKey: replayKey(year, round, session),
    enabled,
    queryFn: () => fetchReplay(year, round, session, REPLAY_STEP, window.location.origin),
    staleTime: REPLAY_STALE_MS,
    gcTime: REPLAY_STALE_MS,
    retry: (count, error) => !(error instanceof ReplayLoadError && error.status === 404) && count < 1,
  });
}
