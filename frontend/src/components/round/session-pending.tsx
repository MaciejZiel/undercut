"use client";

import { Countdown } from "@/components/dashboard/countdown";
import { useNow } from "@/components/dashboard/use-now";
import { EmptyState } from "@/components/states/empty-state";

const HOUR = 3_600_000;
/** After this long a session without results is treated as a data problem, not as "still processing". */
const OVERDUE = 24 * HOUR;
const ISSUES = "https://github.com/MaciejZiel/undercut/issues";

/**
 * A session with no results, told apart by the clock: not started yet (countdown), finished a short
 * while ago (results are on their way) or long ago (we are missing the data).
 */
export function SessionPending({ label, startUtc, backHref, backLabel }: { label: string; startUtc: string | null; backHref: string; backLabel: string }) {
  const now = useNow(1000);
  const start = startUtc ? Date.parse(startUtc) : NaN;

  if (Number.isNaN(start)) {
    return <EmptyState title={`${label} time to be confirmed`} description="The start time is not published yet." action={{ label: backLabel, href: backHref }} />;
  }
  if (now === null) return <div className="skeleton h-40" aria-hidden="true" />;
  if (now < start) {
    return (
      <section aria-labelledby="pending-h" className="border-y border-fg py-6">
        <h2 id="pending-h" className="eyebrow">
          {label} starts in
        </h2>
        <div className="mt-3">
          <Countdown target={startUtc as string} clock />
        </div>
      </section>
    );
  }
  if (now - start < OVERDUE) {
    return (
      <EmptyState
        title="Results are on their way"
        description={`${label} results usually appear within two hours of the chequered flag. This page updates when you reload it.`}
      />
    );
  }
  return (
    <EmptyState
      title="We do not have this result yet"
      description={`The ${label.toLowerCase()} took place, but the data source has not published its results. If it stays empty, tell us and we will look into it.`}
      action={{ label: "Report it on GitHub", href: ISSUES }}
    />
  );
}
