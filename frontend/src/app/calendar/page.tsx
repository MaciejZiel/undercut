import { Suspense } from "react";
import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState } from "@/components/states/empty-state";
import { LoadingSkeleton } from "@/components/states/loading-skeleton";
import { CalendarView } from "@/components/calendar/calendar-view";
import { getCalendar } from "@/components/calendar/data";
import { icsHref } from "@/components/calendar/time";
import { parseIntParam } from "@/lib/url";

export const metadata: Metadata = {
  title: "Calendar",
  description: "Every round of the season with session times in your time zone, a countdown and calendar export.",
};

export default function CalendarPage({ searchParams }: PageProps<"/calendar">) {
  return (
    <>
      <PageHeader title="Calendar" description="Every round of the season with dates, status and session times." />
      <Suspense fallback={<LoadingSkeleton variant="cards" rows={6} label="Loading the calendar" />}>
        <CalendarContent searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function CalendarContent({ searchParams }: { searchParams: PageProps<"/calendar">["searchParams"] }) {
  const year = parseIntParam((await searchParams).year, { min: 1950, max: 2100 });
  const calendar = await getCalendar(year);
  if (calendar === null) {
    return (
      <EmptyState
        title="No calendar for that season"
        description="That season does not exist. Open the current calendar instead."
        action={{ label: "Current calendar", href: "/calendar" }}
      />
    );
  }
  if (calendar.year === null || calendar.rounds.length === 0) {
    return (
      <EmptyState
        title="No rounds yet"
        description="The calendar appears as soon as it is imported."
        action={{ label: "Browse seasons", href: "/seasons" }}
      />
    );
  }
  return (
    <>
      <div className="mb-5 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-xl font-extrabold tracking-tight">{calendar.year} season</h2>
        <a href={icsHref(calendar.year)} className="text-sm font-semibold text-muted hover:text-accent hover:underline">
          Add the whole season to your calendar
        </a>
      </div>
      <CalendarView year={calendar.year} rounds={calendar.rounds} />
    </>
  );
}
