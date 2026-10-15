"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { QueryState } from "@/components/account/query-state";
import { RequireAuth } from "@/components/account/require-auth";
import { DataTable, Th } from "@/components/ui/data-table";
import { fetchHistory, predictKeys, SLOTS, type HistoryRow, type Pick } from "@/lib/predict/api";

function label(d: { name: string; code: string | null } | null | undefined): string {
  return d ? (d.code ?? d.name) : "—";
}

function slotText(p: Pick | null | undefined): string {
  if (!p) return "—";
  return `${label(p.p1)} / ${label(p.p2)} / ${label(p.p3)}`;
}

export function HistoryScreen() {
  return (
    <RequireAuth
      explain={{
        title: "Your picks live here",
        description: "Every podium you call is saved with the points it earned. Sign in to see yours.",
      }}
    >
      <HistoryBody />
    </RequireAuth>
  );
}

function HistoryBody() {
  const query = useQuery({ queryKey: predictKeys.history, queryFn: fetchHistory });
  return (
    <QueryState
      query={query}
      isEmpty={(rows) => rows.length === 0}
      empty={{ title: "No picks yet", description: "Make your first pick for the next race.", action: { label: "Predict the next race", href: "/predict" } }}
      errorTitle="Could not load your picks"
    >
      {(rows) => (
        <DataTable caption="My predictions" minWidth="44rem">
          <thead>
            <tr>
              <Th>Round</Th>
              <Th>Podium pick</Th>
              <Th>Pole</Th>
              <Th>Fastest lap</Th>
              <Th>Result</Th>
              <Th align="right">Points</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <HistoryTr key={r.round ? `${r.round.year}-${r.round.round}` : i} row={r} />
            ))}
          </tbody>
        </DataTable>
      )}
    </QueryState>
  );
}

function HistoryTr({ row }: { row: HistoryRow }) {
  const { round, pick, result, points } = row;
  return (
    <tr className="border-b border-line last:border-b-0 align-top">
      <td className="px-3 py-2.5">
        {round ? (
          <Link href={`/predict/${round.year}/${round.round}`} className="font-semibold text-accent underline">
            {round.year} {round.name}
          </Link>
        ) : (
          "—"
        )}
      </td>
      <td className="timing px-3 py-2.5">{slotText(pick)}</td>
      <td className="timing px-3 py-2.5">{label(pick.pole)}</td>
      <td className="timing px-3 py-2.5">{label(pick.fastest_lap)}</td>
      <td className="timing px-3 py-2.5">
        {result ? (
          <>
            {slotText(result)}
            <span className="block text-xs text-muted">
              {SLOTS.slice(3).map((s) => `${s.label}: ${label(result[s.key])}`).join(", ")}
            </span>
          </>
        ) : (
          <span className="text-muted">Not scored yet</span>
        )}
      </td>
      <td className="timing px-3 py-2.5 text-right font-bold">
        {points ?? "—"}
      </td>
    </tr>
  );
}
