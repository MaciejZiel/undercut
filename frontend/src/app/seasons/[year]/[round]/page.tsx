import { Suspense } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { DetailPageSkeleton } from "@/components/states/page-skeletons";
import { EmptyState } from "@/components/states/empty-state";
import { Badge, CircuitLink, Nationality } from "@/components/ui/entity-links";
import { QualifyingResultsTable, RaceResultsTable } from "@/components/round/results-tables";
import { getRound, getRoundResults, type QualifyingResults, type RaceResults } from "@/lib/api/queries";
import { formatDate, formatLength } from "@/lib/format";
import { roundHref, seasonHref } from "@/lib/routes";
import { availableTabs, pickTab } from "@/lib/sessions";
import { AnalyticsPanel } from "@/components/analytics/analytics-panel";
import { pickView, viewHref, visibleViews } from "@/components/analytics/round-views";
import { ReplayPanel } from "@/components/replay/replay-panel";
import { first, parseIntParam } from "@/lib/url";

type Props = PageProps<"/seasons/[year]/[round]">;

function parseRoute(p: { year: string; round: string }) {
  const year = parseIntParam(p.year, { min: 1950, max: 2100 });
  const round = parseIntParam(p.round, { max: 60 });
  return year && round ? { year, round } : null;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const route = parseRoute(await params);
  const round = route ? await getRound(route.year, route.round) : null;
  if (!round) return { title: "Round not found" };
  return {
    title: `${round.year} ${round.name}`,
    description: `${round.name} ${round.year} at ${round.circuit.name}: race, sprint and qualifying results.`,
  };
}

export default function RoundPage({ params, searchParams }: Props) {
  return (
    <Suspense fallback={<DetailPageSkeleton />}>
      <RoundDetail params={params} searchParams={searchParams} />
    </Suspense>
  );
}

async function RoundDetail({ params, searchParams }: Props) {
  const route = parseRoute(await params);
  const round = route ? await getRound(route.year, route.round) : null;
  if (!route || !round) notFound();

  const requested = first((await searchParams).session);
  const tabs = availableTabs(round.sessions);
  const active = pickTab(requested, tabs, round.sessions);
  const defaultTab = pickTab(undefined, tabs, round.sessions);
  const views = visibleViews(round.year);
  const view = pickView(first((await searchParams).view), round.year);
  const base = roundHref(round.year, round.round);
  const sessionInfo = active ? round.sessions.find((s) => s.type === active.type) : undefined;
  const results = active ? await getRoundResults(round.year, round.round, active.type) : null;

  return (
    <>
      <div className="mb-6">
        <Breadcrumbs
          items={[
            { label: "Seasons", href: "/seasons" },
            { label: String(round.year), href: seasonHref(round.year) },
            { label: round.name },
          ]}
        />
        <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
          {round.year} {round.name}
        </h1>
        <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-muted">
          <span>Round {round.round}</span>
          <span>{formatDate(round.date)}</span>
          <CircuitLink slug={round.circuit.slug} name={round.circuit.name} />
          {round.circuit.country && <Nationality value={round.circuit.country} />}
          {formatLength(round.circuit.length_m) && <span className="timing">{formatLength(round.circuit.length_m)}</span>}
          {round.scheduled_laps != null && <span className="timing">{round.scheduled_laps} laps</span>}
          {round.is_cancelled && <Badge tone="danger">Cancelled</Badge>}
        </p>
        <nav aria-label="Rounds" className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm font-semibold">
          {round.previous_round && (
            <Link href={roundHref(round.previous_round.year, round.previous_round.round)} className="text-muted hover:text-fg">
              <span aria-hidden="true">&larr; </span>
              Previous: {round.previous_round.name}
            </Link>
          )}
          {round.next_round && (
            <Link href={roundHref(round.next_round.year, round.next_round.round)} className="text-muted hover:text-fg">
              Next: {round.next_round.name}
              <span aria-hidden="true"> &rarr;</span>
            </Link>
          )}
        </nav>
      </div>

      {tabs.length > 0 && (
        <nav aria-label="Sessions" className="mb-4 flex gap-1 border-b border-line">
          {tabs.map((t) => {
            const current = t.key === active?.key;
            return (
              <Link
                key={t.key}
                href={viewHref(base, { session: t.key === defaultTab?.key ? null : t.key, view })}
                aria-current={current ? "page" : undefined}
                className={`t-fast -mb-px border-b-2 px-4 py-2.5 text-sm font-bold ${
                  current ? "border-accent text-fg" : "border-transparent text-muted hover:text-fg"
                }`}
              >
                {t.label}
              </Link>
            );
          })}
        </nav>
      )}
      {views.length > 1 && (
        <nav aria-label="Views" className="mb-4 flex flex-wrap gap-2">
          {views.map((v) => (
            <Link
              key={v.key}
              href={viewHref(base, { session: active && active.key !== defaultTab?.key ? active.key : null, view: v.key })}
              aria-current={v.key === view ? "page" : undefined}
              className={`t-fast rounded-md border px-3 py-1.5 text-sm font-semibold ${
                v.key === view ? "border-accent bg-accent-soft text-accent" : "border-line text-muted hover:text-fg"
              }`}
            >
              {v.label}
            </Link>
          ))}
        </nav>
      )}
      {round.year < 2023 && (
        <p className="mb-4 text-sm text-muted">Detailed analytics are available from the 2023 season.</p>
      )}

      {active && (view === "analysis" || view === "strategy") ? (
        <AnalyticsPanel key={`${view}-${active.type}`} view={view} year={round.year} round={round.round} session={active.type} />
      ) : active && view === "replay" ? (
        <ReplayPanel key={active.type} year={round.year} round={round.round} session={active.type} roundName={round.name} label={active.label} />
      ) : !active || results === null || results.results.length === 0 ? (
        <EmptyState
          title={round.is_cancelled ? "This round was cancelled" : "No results yet"}
          description={
            round.is_cancelled
              ? "No sessions were held."
              : "Results appear here once the session has finished."
          }
          action={{ label: `Back to ${round.year} calendar`, href: seasonHref(round.year) }}
        />
      ) : (
        <section aria-labelledby="results-h">
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <h2 id="results-h" className="text-xl font-extrabold tracking-tight">
              {active.label} results
            </h2>
            {sessionInfo && sessionInfo.status !== "results_final" && <Badge tone="accent">Preliminary</Badge>}
          </div>
          {active.type === "Q" ? (
            <QualifyingResultsTable
              results={(results as QualifyingResults).results}
              caption={`${round.year} ${round.name} qualifying results`}
            />
          ) : (
            <RaceResultsTable
              results={(results as RaceResults).results}
              caption={`${round.year} ${round.name} ${active.label.toLowerCase()} results`}
            />
          )}
        </section>
      )}
    </>
  );
}
