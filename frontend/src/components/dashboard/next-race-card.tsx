import Link from "next/link";
import type { components } from "@/lib/api/client";
import { circuitHref, roundHref } from "@/lib/routes";
import { icsHref } from "@/components/calendar/time";
import { Countdown } from "./countdown";
import { WeekendSchedule } from "./weekend-schedule";

type Session = components["schemas"]["CalendarSession"];

/** The next race weekend: the name set large, the clock, and every session in the viewer's time zone. */
export function NextRaceCard({
  year,
  round,
  name,
  circuit,
  raceStartUtc,
  sessions,
}: {
  year: number;
  round: number;
  name: string;
  date?: string;
  circuit: { slug: string; name: string; country?: string | null; locality?: string | null };
  /** Exact lights-out moment when known; otherwise only the date is shown. */
  raceStartUtc: string | null;
  sessions: Session[];
}) {
  const place = [circuit.locality, circuit.country].filter(Boolean).join(", ");
  return (
    <article
      aria-labelledby="next-race-h"
      className="grid grid-cols-1 gap-x-12 gap-y-10 border-b border-line pb-12 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]"
    >
      <div>
        <p className="label">
          Next race · Round {round}
          {place ? ` · ${place}` : ""}
        </p>
        <h2 id="next-race-h" className="display mt-3 text-6xl sm:text-7xl lg:text-8xl">
          <Link href={roundHref(year, round)} className="hover:underline decoration-flag decoration-[6px] underline-offset-[6px]">
            {name}
          </Link>
        </h2>
        <p className="mt-5 max-w-[46ch] text-lg text-muted">
          <Link href={circuitHref(circuit.slug)} className="font-semibold text-fg underline-offset-2 hover:underline">
            {circuit.name}
          </Link>
        </p>
        <div className="mt-8">
          {raceStartUtc ? <Countdown target={raceStartUtc} /> : <p className="text-sm text-muted">Start time to be confirmed</p>}
        </div>
        <p className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-[0.9375rem] font-semibold">
          <a href={icsHref(year, round)} className="underline underline-offset-4 hover:no-underline">
            Add the weekend to my calendar
          </a>
          <Link href="/calendar" className="text-muted hover:text-fg">
            Full calendar &rarr;
          </Link>
        </p>
      </div>
      <div className="self-end">
        <WeekendSchedule sessions={sessions} />
      </div>
    </article>
  );
}
