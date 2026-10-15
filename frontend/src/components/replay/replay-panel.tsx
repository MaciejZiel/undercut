"use client";

import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { LoadingSkeleton } from "@/components/states/loading-skeleton";
import { ReplayLoadError, useReplay, type ReplaySession } from "@/lib/replay/api";
import { ReplayView } from "./replay-view";

/** Replay tab body: fetches the (cached) document, then hands it to the player. */
export function ReplayPanel({
  year,
  round,
  session,
  roundName,
  label,
}: {
  year: number;
  round: number;
  session: ReplaySession | "Q";
  roundName: string;
  label: string;
}) {
  const query = useReplay(year, round, session === "Q" ? "RACE" : session, session !== "Q");
  if (session === "Q") {
    return <EmptyState title="No replay for qualifying" description="Replay is available for races and sprints." />;
  }
  if (query.isPending) return <LoadingSkeleton variant="table" rows={20} label="Loading replay" />;
  if (query.isError) {
    if (query.error instanceof ReplayLoadError && query.error.status === 404) {
      return <EmptyState title="No replay for this session" description="Replay data is not available for it." />;
    }
    return <ErrorState title="Could not load the replay" onRetry={() => void query.refetch()} />;
  }
  return <ReplayView doc={query.data} caption={`${year} ${roundName} ${label.toLowerCase()} replay timing`} />;
}
