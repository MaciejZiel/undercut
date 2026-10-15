import { Suspense } from "react";
import type { Metadata } from "next";
import { pageMetadata, absoluteUrl } from "@/lib/seo";
import { JsonLd } from "@/components/seo/json-ld";
import { notFound } from "next/navigation";
import Link from "next/link";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { DetailPageSkeleton } from "@/components/states/page-skeletons";
import { EmptyState } from "@/components/states/empty-state";
import { Badge, CircuitLink, Nationality } from "@/components/ui/entity-links";
import { PracticeResultsTable, QualifyingResultsTable, RaceResultsTable } from "@/components/round/results-tables";
import { getRound, getRoundResults, type PracticeResults, type QualifyingResults, type RaceResults } from "@/lib/api/queries";
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
  return pageMetadata({
    title: `${round.year} ${round.name}`,
    description: `${round.name} ${round.year} at ${round.circuit.name}: race, sprint and qualifying results.`,
    path: roundHref(round.year, round.round),
  });
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
  // Analysis, strategy and replay exist for race, sprint and qualifying only.
  const analytic = active && ["RACE", "SPRINT", "Q"].includes(active.type) ? (active.type as "RACE" | "SPRINT" | "Q") : null;
  const views = analytic ? visibleViews(round.year) : [];
  const view = analytic ? pickView(first((await searchParams).view), round.year) : "results";
  const base = roundHref(round.year, round.round);
  const sessionInfo = active ? round.sessions.find((s) => s.type === active.type) : undefined;
  const results = active ? await getRoundResults(round.year, round.round, active.type) : null;

  return (
    <>
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "SportsEvent",
          name: `${round.year} ${round.name}`,
          sport: "Formula One",
          startDate: round.date,
          eventStatus: round.is_cancelled ? "https://schema.org/EventCancelled" : "https://schema.org/EventScheduled",
          location: {
            "@type": "Place",
            name: round.circuit.name,
            ...(round.circuit.country ? { address: { "@type": "PostalAddress", addressCountry: round.circuit.country } } : {}),
          },
          url: absoluteUrl(roundHref(round.year, round.round)),
        }}
      />
      <div className="mb-8">
        <Breadcrumbs
          items={[
            { label: "Seasons", href: "/seasons" },
            { label: String(round.year), href: seasonHref(round.year) },
            { label: round.name },
          ]}
        />
        <h1 className="display text-5xl sm:text-7xl">
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
        <nav aria-label="Sessions" className="mb-5 flex flex-wrap gap-1 border-b border-line">
          {tabs.map((t) => {
            const current = t.key === active?.key;
            return (
              <Link
                key={t.key}
                href={viewHref(base, { session: t.key === defaultTab?.key ? null : t.key, view })}
                aria-current={current ? "page" : undefined}
                className={`t-fast -mb-px border-b-4 px-4 py-3 text-[0.9375rem] font-bold ${
                  current ? "border-flag text-fg" : "border-transparent text-muted hover:text-fg"
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
              className={`t-fast rounded-sm border px-3.5 py-2 text-sm font-semibold ${
                v.key === view ? "border-fg bg-fg text-bg" : "border-line text-muted hover:border-fg hover:text-fg"
              }`}
            >
              {v.label}
            </Link>
          ))}
        </nav>
      )}
      {analytic && round.year < 2023 && (
        <p className="mb-4 text-sm text-muted">Detailed analytics are available from the 2023 season.</p>
      )}

      {analytic && (view === "analysis" || view === "strategy") ? (
        <AnalyticsPanel key={`${view}-${analytic}`} view={view} year={round.year} round={round.round} session={analytic} />
      ) : analytic && view === "replay" ? (
        <ReplayPanel key={analytic} year={round.year} round={round.round} session={analytic} roundName={round.name} label={active?.label ?? ""} />
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
            <h2 id="results-h" className="text-2xl font-bold tracking-tight">
              {active.label} results
            </h2>
            {sessionInfo && sessionInfo.status !== "results_final" && <Badge tone="accent">Preliminary</Badge>}
          </div>
          {active.type === "Q" || active.type === "SQ" ? (
            <QualifyingResultsTable
              results={(results as QualifyingResults).results}
              prefix={active.type === "SQ" ? "SQ" : "Q"}
              caption={`${round.year} ${round.name} ${active.label.toLowerCase()} results`}
            />
          ) : active.type.startsWith("FP") ? (
            <PracticeResultsTable
              results={(results as PracticeResults).results}
              caption={`${round.year} ${round.name} ${active.label.toLowerCase()} results`}
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
