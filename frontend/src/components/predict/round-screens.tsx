"use client";

import { useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo } from "react";
import { EmptyState } from "@/components/states/empty-state";
import { LoadingSkeleton } from "@/components/states/loading-skeleton";
import { ErrorState } from "@/components/states/error-state";
import { QueryState } from "@/components/account/query-state";
import { primaryButton, Notice } from "@/components/account/form-parts";
import {
  fetchPickableDrivers,
  fetchRoundState,
  findNextRound,
  predictKeys,
  type PickableDriver,
  type RoundStateResult,
} from "@/lib/predict/api";
import { Countdown } from "./countdown";
import { PickForm } from "./pick-form";

/** /predict: the next round that is open for predictions, with its countdown. Public. */
export function PredictHome() {
  const client = useQueryClient();
  const next = useQuery({ queryKey: predictKeys.next, queryFn: findNextRound, staleTime: 30_000 });
  return (
    <QueryState
      query={next}
      skeleton={<LoadingSkeleton variant="cards" rows={1} label="Loading the next race" />}
      errorTitle="Could not load the next race"
    >
      {(data) => {
        if (data.kind === "none") {
          return <EmptyState title="No race to predict" description="There is no upcoming round right now. Check the calendar." action={{ label: "Open the calendar", href: "/calendar" }} />;
        }
        const { state, skewMs } = data.result;
        const href = `/predict/${state.round.year}/${state.round.round}`;
        const open = state.status === "open";
        return (
          <section aria-labelledby="next-h" className="border-t border-line pt-6">
            <p className="text-sm font-bold text-muted">
              {state.round.year} round {state.round.round}
            </p>
            <h2 id="next-h" className="mt-1 heading text-xl sm:text-[1.375rem]">
              {state.round.name}
            </h2>
            <div className="mt-4">
              {open ? (
                <>
                  <p className="text-sm text-muted">Predictions close in</p>
                  <Countdown closesAt={state.closes_at} skewMs={skewMs} onExpire={() => void client.invalidateQueries({ queryKey: predictKeys.next })} />
                </>
              ) : state.status === "closed" ? (
                <p className="font-semibold">Predictions for this round are closed.</p>
              ) : (
                <p className="text-muted">The lock time is not known yet. Picks open once the qualifying time is published.</p>
              )}
            </div>
            {state.my_pick && <p className="mt-3 text-sm">Your pick: {[state.my_pick.p1, state.my_pick.p2, state.my_pick.p3].map((d) => d?.code ?? d?.name ?? "—").join(" / ")}</p>}
            <div className="mt-5 flex flex-wrap gap-3">
              <Link href={href} className={primaryButton}>
                {!open ? "View round" : state.my_pick ? "Edit your pick" : "Predict the podium"}
              </Link>
            </div>
          </section>
        );
      }}
    </QueryState>
  );
}

/** /predict/[year]/[round]: the five-field form; read-only once the server says it is closed. */
export function PredictRoundScreen({ year, round }: { year: number; round: number }) {
  return (
    <RoundBody year={year} round={round} />
  );
}

function RoundBody({ year, round }: { year: number; round: number }) {
  const client = useQueryClient();
  const state = useQuery({ queryKey: predictKeys.round(year, round), queryFn: () => fetchRoundState(year, round), staleTime: 15_000 });
  const drivers = useQuery({ queryKey: predictKeys.drivers(year), queryFn: () => fetchPickableDrivers(year), staleTime: 10 * 60_000 });

  return (
    <QueryState query={state} skeleton={<LoadingSkeleton variant="cards" rows={1} label="Loading the round" />} errorTitle="Could not load this round">
      {(result) => (
        <div>
          <p className="mb-4 text-lg font-bold">{result.state.round.name}</p>
          <DriversGate drivers={drivers} result={result}>
            {(list) => (
              <PickForm
                // Remount when the server's view of the round changes (open -> closed).
                key={result.state.status}
                year={year}
                round={round}
                result={result}
                drivers={list}
                onExpire={() => void client.invalidateQueries({ queryKey: predictKeys.round(year, round) })}
              />
            )}
          </DriversGate>
        </div>
      )}
    </QueryState>
  );
}

function DriversGate({
  drivers,
  result,
  children,
}: {
  drivers: UseQueryResult<PickableDriver[], unknown>;
  result: RoundStateResult;
  children: (list: PickableDriver[]) => React.ReactNode;
}) {
  const pickedDrivers = useMemo(() => {
    const p = result.state.my_pick;
    if (!p) return [] as PickableDriver[];
    return [p.p1, p.p2, p.p3, p.pole, p.fastest_lap].flatMap((d) => (d ? [{ id: d.id, name: d.name, code: d.code, number: null }] : []));
  }, [result.state.my_pick]);

  if (result.state.status === "closed") return <>{children(pickedDrivers)}</>;
  if (drivers.isPending) return <LoadingSkeleton variant="cards" rows={2} label="Loading drivers" />;
  if (drivers.isError) return <ErrorState title="Could not load the drivers" onRetry={() => void drivers.refetch()} />;
  const merged = [...drivers.data];
  for (const d of pickedDrivers) if (!merged.some((m) => m.id === d.id)) merged.push(d);
  if (merged.length === 0) {
    return <Notice tone="info">No drivers are available for this season yet.</Notice>;
  }
  return <>{children(merged)}</>;
}
