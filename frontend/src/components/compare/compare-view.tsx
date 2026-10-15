"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { createApiClient, type components } from "@/lib/api/client";
import { formatInteger, formatLapTime, formatPoints } from "@/lib/format";
import { driverHref } from "@/lib/routes";
import { DataTable, RowTh, Td, Th, Tr } from "@/components/ui/data-table";
import { Dash } from "@/components/ui/value";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { LoadingSkeleton } from "@/components/states/loading-skeleton";
import { compareHref, isReady, MAX_SEASON, MIN_SEASON, parseSeason, type CompareState } from "./compare-url";
import { DriverPicker, type PickedDriver } from "./driver-picker";

type Compare = components["schemas"]["Compare"];
type Stats = components["schemas"]["CareerStats"];

class CompareError extends Error {
  constructor(readonly status: number) {
    super(`Compare request failed with status ${status}`);
  }
}

async function fetchCompare(state: { a: string; b: string; season: number | null }, signal: AbortSignal): Promise<Compare> {
  const { data, response } = await createApiClient(window.location.origin).GET("/api/v1/compare/", {
    params: { query: { a: state.a, b: state.b, season: state.season ?? undefined } },
    signal,
  });
  if (!response.ok || !data) throw new CompareError(response.status);
  return data;
}

/** Which side has the larger value; null when either is unknown or they are equal. */
export function leader(a: number | null | undefined, b: number | null | undefined): "a" | "b" | null {
  if (a == null || b == null || a === b) return null;
  return a > b ? "a" : "b";
}

/** Signed difference in seconds, "+0.123 s"; null stays null. */
export function formatDelta(ms: number | null | undefined): string | null {
  if (ms == null || !Number.isFinite(ms)) return null;
  const sign = ms > 0 ? "+" : ms < 0 ? "-" : "";
  return `${sign}${(Math.abs(ms) / 1000).toFixed(3)} s`;
}

export function CompareView({ initial }: { initial: CompareState }) {
  const router = useRouter();
  const [names, setNames] = useState<Record<string, string>>({});
  const [seasonText, setSeasonText] = useState(initial.season ? String(initial.season) : "");
  const [seasonError, setSeasonError] = useState<string | null>(null);
  const state = initial;
  const ready = isReady(state);

  const query = useQuery({
    queryKey: ["compare", state.a, state.b, state.season],
    queryFn: ({ signal }) => fetchCompare(state as { a: string; b: string; season: number | null }, signal),
    enabled: ready,
    retry: (count, error) => !(error instanceof CompareError && error.status < 500) && count < 1,
  });

  const nameOf = (slug: string | null, fromApi?: string) => (slug ? (names[slug] ?? fromApi ?? null) : null);

  function go(next: CompareState) {
    router.replace(compareHref(next), { scroll: false });
  }

  function pick(side: "a" | "b", d: PickedDriver) {
    setNames((n) => ({ ...n, [d.slug]: d.name }));
    go({ ...state, [side]: d.slug });
  }

  function submitSeason(e: FormEvent) {
    e.preventDefault();
    const text = seasonText.trim();
    if (text === "") {
      setSeasonError(null);
      go({ ...state, season: null });
      return;
    }
    const season = parseSeason(text);
    if (season === null) {
      setSeasonError(`Enter a year between ${MIN_SEASON} and ${MAX_SEASON}, or leave it empty.`);
      return;
    }
    setSeasonError(null);
    go({ ...state, season });
  }

  const same = state.a !== null && state.a === state.b;

  return (
    <div className="flex flex-col gap-8">
      <form onSubmit={submitSeason} className="grid grid-cols-1 gap-4 border-y border-line py-4 sm:grid-cols-3">
        <DriverPicker
          label="First driver"
          value={state.a ? { slug: state.a, name: nameOf(state.a, query.data?.a.driver.name) } : null}
          onSelect={(d) => pick("a", d)}
          disabledSlug={state.b}
        />
        <DriverPicker
          label="Second driver"
          value={state.b ? { slug: state.b, name: nameOf(state.b, query.data?.b.driver.name) } : null}
          onSelect={(d) => pick("b", d)}
          disabledSlug={state.a}
        />
        <div>
          <label htmlFor="compare-season" className="mb-1 block text-sm font-semibold">
            Season (optional)
          </label>
          <div className="flex gap-2">
            <input
              id="compare-season"
              type="text"
              inputMode="numeric"
              placeholder="All seasons"
              value={seasonText}
              onChange={(e) => setSeasonText(e.target.value)}
              aria-invalid={seasonError ? true : undefined}
              aria-describedby={seasonError ? "compare-season-err" : undefined}
              className="w-full min-w-0 rounded-md border border-line-strong bg-bg px-3 py-2 text-sm"
            />
            <button type="submit" className="t-fast shrink-0 whitespace-nowrap rounded-md bg-accent px-3 py-2 text-sm font-bold text-accent-fg hover:opacity-90">
              Apply
            </button>
          </div>
          {seasonError && (
            <p id="compare-season-err" role="alert" className="mt-1 text-sm text-danger">
              {seasonError}
            </p>
          )}
        </div>
      </form>

      {same && (
        <p role="alert" className="text-danger">
          Pick two different drivers.
        </p>
      )}
      {!ready && !same && (
        <EmptyState title="Pick two drivers" description="Choose a first and a second driver to see them side by side." />
      )}
      {ready && query.isPending && <LoadingSkeleton variant="table" rows={7} label="Loading the comparison" />}
      {ready && query.isError && <CompareFailure error={query.error} onRetry={() => void query.refetch()} />}
      {ready && query.data && <Comparison data={query.data} />}
    </div>
  );
}

function CompareFailure({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  if (error instanceof CompareError && error.status === 404) {
    return (
      <EmptyState
        title="Driver not found"
        description="One of the drivers in the link does not exist. Pick the drivers again."
        action={{ label: "Start over", href: "/compare" }}
      />
    );
  }
  if (error instanceof CompareError && error.status === 400) {
    return <EmptyState title="Cannot compare these drivers" description="Check the drivers and the season and try again." />;
  }
  return <ErrorState title="Could not load the comparison" onRetry={onRetry} />;
}

const STAT_ROWS: { label: string; key: keyof Stats; format: (v: number | null | undefined) => string | null }[] = [
  { label: "Starts", key: "starts", format: formatInteger },
  { label: "Wins", key: "wins", format: formatInteger },
  { label: "Podiums", key: "podiums", format: formatInteger },
  { label: "Pole positions", key: "poles", format: formatInteger },
  { label: "Fastest laps", key: "fastest_laps", format: formatInteger },
  { label: "Titles", key: "titles", format: formatInteger },
  { label: "Career points", key: "points", format: formatPoints },
];

function Comparison({ data }: { data: Compare }) {
  const { a, b, head_to_head: h2h } = data;
  return (
    <>
      <section aria-labelledby="cmp-stats-h">
        <h2 id="cmp-stats-h" className="mb-3 heading text-xl sm:text-[1.375rem]">
          Career statistics
        </h2>
        <DataTable caption={`Career statistics of ${a.driver.name} and ${b.driver.name}`} minWidth="0">
          <thead>
            <tr>
              <Th>Statistic</Th>
              <Th align="right">
                <Link href={driverHref(a.driver.slug)} className="hover:text-accent hover:underline">
                  {a.driver.name}
                </Link>
              </Th>
              <Th align="right">
                <Link href={driverHref(b.driver.slug)} className="hover:text-accent hover:underline">
                  {b.driver.name}
                </Link>
              </Th>
            </tr>
          </thead>
          <tbody>
            {STAT_ROWS.map((row) => {
              const va = a.stats[row.key] as number | null | undefined;
              const vb = b.stats[row.key] as number | null | undefined;
              const lead = leader(va, vb);
              const cell = (v: number | null | undefined, side: "a" | "b") => (
                <Td align="right" className={`timing ${lead === side ? "font-extrabold" : ""}`}>
                  {row.format(v) ?? <Dash />}
                  {lead === side && <span className="sr-only"> (higher)</span>}
                </Td>
              );
              return (
                <Tr key={row.key}>
                  <RowTh>{row.label}</RowTh>
                  {cell(va, "a")}
                  {cell(vb, "b")}
                </Tr>
              );
            })}
          </tbody>
        </DataTable>
      </section>

      <section aria-labelledby="cmp-h2h-h">
        <h2 id="cmp-h2h-h" className="mb-1 heading text-xl sm:text-[1.375rem]">
          Head to head
        </h2>
        <p className="mb-3 text-sm text-muted">
          {data.season ? `${data.season} season only.` : "All seasons."} {h2h.races_together} races together,{" "}
          {h2h.same_team_races} of them for the same team.
        </p>
        {h2h.races_together === 0 ? (
          <EmptyState title="Never raced each other" description="These drivers have no race in common, so there is no head to head." />
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Duel
              title="Race finishes"
              note="Races where both were classified and not level on position."
              aName={a.driver.name}
              bName={b.driver.name}
              aAhead={h2h.race.a_ahead}
              bAhead={h2h.race.b_ahead}
              total={h2h.race.both_finished}
              totalLabel="races compared"
            />
            <Duel
              title="Qualifying duels"
              note="Qualifying position from 1994, starting grid position before."
              aName={a.driver.name}
              bName={b.driver.name}
              aAhead={h2h.qualifying.a_ahead}
              bAhead={h2h.qualifying.b_ahead}
              total={h2h.qualifying.compared}
              totalLabel="sessions compared"
            />
          </div>
        )}
      </section>

      {h2h.teammate_seasons.length > 0 && (
        <section aria-labelledby="cmp-lap-h">
          <h2 id="cmp-lap-h" className="mb-3 heading text-xl sm:text-[1.375rem]">
            Team mates: median race laps
          </h2>
          <div className="flex flex-col gap-6">
            {h2h.teammate_seasons.map((s) => (
              <TeammateSeason key={`${s.year}-${s.team_slug}`} season={s} aName={a.driver.name} bName={b.driver.name} />
            ))}
          </div>
        </section>
      )}
    </>
  );
}

function Duel({
  title,
  note,
  aName,
  bName,
  aAhead,
  bAhead,
  total,
  totalLabel,
}: {
  title: string;
  note: string;
  aName: string;
  bName: string;
  aAhead: number;
  bAhead: number;
  total: number;
  totalLabel: string;
}) {
  const sum = aAhead + bAhead;
  const share = sum > 0 ? Math.round((aAhead / sum) * 100) : null;
  return (
    <article className="border-t border-line pt-4">
      <h3 className="font-bold">{title}</h3>
      <p className="mb-3 text-sm text-muted">{note}</p>
      {total === 0 ? (
        <p className="text-sm text-muted">
          <Dash label="Nothing to compare" /> Nothing to compare.
        </p>
      ) : (
        <>
          <div className="flex items-baseline justify-between gap-3">
            <p>
              <span className="timing text-3xl font-extrabold">{aAhead}</span>
              <span className="ml-2 text-sm text-muted">{aName}</span>
            </p>
            <p className="text-right">
              <span className="mr-2 text-sm text-muted">{bName}</span>
              <span className="timing text-3xl font-extrabold">{bAhead}</span>
            </p>
          </div>
          <div aria-hidden="true" className="mt-2 flex h-2 overflow-hidden rounded-full bg-surface-2">
            {share !== null && <div className="h-full bg-accent" style={{ width: `${share}%` }} />}
          </div>
          <p className="mt-2 text-sm text-muted">
            <span className="timing">{total}</span> {totalLabel}
          </p>
          <p className="sr-only">
            {aName} ahead {aAhead} times, {bName} ahead {bAhead} times.
          </p>
        </>
      )}
    </article>
  );
}

function TeammateSeason({
  season,
  aName,
  bName,
}: {
  season: Compare["head_to_head"]["teammate_seasons"][number];
  aName: string;
  bName: string;
}) {
  const heading = `${season.year}, ${season.races} ${season.races === 1 ? "race" : "races"} as team mates`;
  if (season.lap_times === null || season.lap_times.length === 0) {
    return (
      <div className="rounded-sm border border-dashed border-line p-4">
        <h3 className="font-bold">{heading}</h3>
        <p className="mt-1 text-sm text-muted">{season.lap_times_reason ?? "No lap-time data for this season."}</p>
      </div>
    );
  }
  return (
    <div>
      <h3 className="mb-2 font-bold">{heading}</h3>
      <DataTable caption={`Median race lap times of ${aName} and ${bName}, ${season.year}`} minWidth="30rem">
        <thead>
          <tr>
            <Th>Round</Th>
            <Th align="right">{aName}</Th>
            <Th align="right">{bName}</Th>
            <Th align="right">Difference</Th>
          </tr>
        </thead>
        <tbody>
          {season.lap_times.map((lap) => (
            <Tr key={lap.round}>
              <RowTh>
                <span className="timing mr-2 text-muted">{lap.round}</span>
                {lap.name}
              </RowTh>
              <Td align="right" className="timing">
                {formatLapTime(lap.a_median_lap_ms) ?? <Dash />}
              </Td>
              <Td align="right" className="timing">
                {formatLapTime(lap.b_median_lap_ms) ?? <Dash />}
              </Td>
              <Td align="right" className="timing">
                {formatDelta(lap.delta_ms) ?? <Dash />}
              </Td>
            </Tr>
          ))}
        </tbody>
      </DataTable>
      <p className="mt-1 text-sm text-muted">Difference is {aName} minus {bName}; a negative value means {aName} was faster.</p>
    </div>
  );
}
