"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { QueryState } from "@/components/account/query-state";
import { inputClass, secondaryButton } from "@/components/account/form-parts";
import { DataTable, Th } from "@/components/ui/data-table";
import { useAuth } from "@/lib/auth/auth-context";
import {
  fetchLeaderboard,
  fetchSeasonRounds,
  fetchSeasonYears,
  predictKeys,
  type Leaderboard,
  type LeaderboardRow,
} from "@/lib/predict/api";

export const LEADERBOARD_PAGE_SIZE = 25;

/** True while the element is outside the viewport. Without IntersectionObserver nothing is pinned. */
export function useOffscreen<T extends Element>(active: boolean) {
  const ref = useRef<T | null>(null);
  const [off, setOff] = useState(false);
  useEffect(() => {
    const node = ref.current;
    if (!active || !node || typeof IntersectionObserver === "undefined") {
      setOff(false);
      return;
    }
    const io = new IntersectionObserver(([entry]) => setOff(!entry.isIntersecting));
    io.observe(node);
    return () => io.disconnect();
  }, [active]);
  return [ref, off] as const;
}

/**
 * Leaderboard table. `league` scopes it to a league (members only). The global board has season
 * and round filters. The signed-in player's own row is pinned to the bottom while it is off-screen.
 */
export function LeaderboardPanel({ league, filters = !league }: { league?: string; filters?: boolean }) {
  const auth = useAuth();
  const [season, setSeason] = useState<number | undefined>();
  const [round, setRound] = useState<number | undefined>();
  const [offset, setOffset] = useState(0);
  const params = { season, round, league, limit: LEADERBOARD_PAGE_SIZE, offset };
  const query = useQuery({ queryKey: predictKeys.leaderboard(params), queryFn: () => fetchLeaderboard(params), placeholderData: (prev) => prev });

  return (
    <div>
      {filters && (
        <Filters
          season={season}
          round={round}
          onSeason={(y) => {
            setSeason(y);
            setRound(undefined);
            setOffset(0);
          }}
          onRound={(r) => {
            setRound(r);
            setOffset(0);
          }}
        />
      )}
      <QueryState
        query={query}
        isEmpty={(d) => d.count === 0 && d.results.length === 0}
        empty={{ title: "No scores yet", description: "Points appear after the first scored race." }}
        errorTitle="Could not load the leaderboard"
        forbidden="Leaderboard not available"
      >
        {(data) => <Table data={data} offset={offset} onOffset={setOffset} ownId={auth.user?.id ?? null} />}
      </QueryState>
    </div>
  );
}

function Filters({
  season,
  round,
  onSeason,
  onRound,
}: {
  season?: number;
  round?: number;
  onSeason: (y: number | undefined) => void;
  onRound: (r: number | undefined) => void;
}) {
  const years = useQuery({ queryKey: predictKeys.seasons, queryFn: fetchSeasonYears, staleTime: 10 * 60_000 });
  const rounds = useQuery({
    queryKey: predictKeys.season(season ?? 0),
    queryFn: () => fetchSeasonRounds(season as number),
    enabled: season !== undefined,
    staleTime: 10 * 60_000,
  });
  return (
    <div className="mb-4 flex flex-wrap gap-4">
      <div>
        <label htmlFor="lb-season" className="mb-1 block text-sm font-semibold">
          Season
        </label>
        <select id="lb-season" className={inputClass} value={season ?? ""} onChange={(e) => onSeason(e.target.value ? Number(e.target.value) : undefined)}>
          <option value="">All seasons</option>
          {years.data?.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="lb-round" className="mb-1 block text-sm font-semibold">
          Round
        </label>
        <select id="lb-round" className={inputClass} disabled={season === undefined} value={round ?? ""} onChange={(e) => onRound(e.target.value ? Number(e.target.value) : undefined)}>
          <option value="">Whole season</option>
          {rounds.data
            ?.filter((r) => r.round != null && !r.is_cancelled)
            .map((r) => (
              <option key={r.round} value={r.round as number}>
                {r.round}. {r.name}
              </option>
            ))}
        </select>
      </div>
    </div>
  );
}

function Table({ data, offset, onOffset, ownId }: { data: Leaderboard; offset: number; onOffset: (n: number) => void; ownId: number | null }) {
  const own = ownId != null ? data.results.find((r) => r.user_id === ownId) : undefined;
  const [ownRef, offscreen] = useOffscreen<HTMLTableRowElement>(!!own);
  const hasPrev = offset > 0;
  const hasNext = offset + data.results.length < data.count;

  return (
    <div>
      <DataTable caption="Prediction leaderboard" minWidth="36rem">
        <thead>
          <tr>
            <Th align="right">Rank</Th>
            <Th>Player</Th>
            <Th align="right">Points</Th>
            <Th align="right">Exact hits</Th>
            <Th align="right">Poles</Th>
            <Th align="right">Picks</Th>
          </tr>
        </thead>
        <tbody>
          {data.results.map((r) => (
            <Row key={`${r.rank}-${r.user_id ?? r.name}`} row={r} mine={r === own} rowRef={r === own ? ownRef : undefined} />
          ))}
        </tbody>
      </DataTable>
      <div className="mt-3 flex items-center justify-between gap-3 text-sm text-muted">
        <span>
          {offset + 1} to {offset + data.results.length} of {data.count}
        </span>
        <span className="flex gap-2">
          <button type="button" className={secondaryButton} disabled={!hasPrev} onClick={() => onOffset(Math.max(0, offset - LEADERBOARD_PAGE_SIZE))}>
            Previous
          </button>
          <button type="button" className={secondaryButton} disabled={!hasNext} onClick={() => onOffset(offset + LEADERBOARD_PAGE_SIZE)}>
            Next
          </button>
        </span>
      </div>
      {own && offscreen && (
        <div
          data-testid="pinned-own-row"
          role="status"
          className="sticky bottom-[4.5rem] z-10 mt-3 flex items-center gap-4 rounded-sm border border-accent bg-surface px-4 py-3 text-sm shadow-lg md:bottom-3"
        >
          <span className="timing font-extrabold">#{own.rank}</span>
          <span className="font-semibold">You ({own.name})</span>
          <span className="timing ml-auto font-bold">{own.points} pts</span>
        </div>
      )}
    </div>
  );
}

function Row({ row, mine, rowRef }: { row: LeaderboardRow; mine: boolean; rowRef?: React.Ref<HTMLTableRowElement> }) {
  return (
    <tr ref={rowRef} aria-current={mine ? "true" : undefined} className={`border-b border-line last:border-b-0 ${mine ? "bg-accent-soft" : ""}`}>
      <td className="timing px-3 py-2.5 text-right font-bold">{row.rank}</td>
      <td className="px-3 py-2.5 font-semibold">
        {row.name}
        {mine && <span className="ml-2 text-xs text-muted">(you)</span>}
      </td>
      <td className="timing px-3 py-2.5 text-right font-bold">{row.points}</td>
      <td className="timing px-3 py-2.5 text-right">{row.exact_hits}</td>
      <td className="timing px-3 py-2.5 text-right">{row.pole_hits}</td>
      <td className="timing px-3 py-2.5 text-right">{row.predictions}</td>
    </tr>
  );
}
