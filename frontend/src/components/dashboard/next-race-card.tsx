import Link from "next/link";
import { formatDate } from "@/lib/format";
import { circuitHref, roundHref } from "@/lib/routes";
import { icsHref } from "@/components/calendar/time";
import { Countdown } from "./countdown";

export function NextRaceCard({
  year,
  round,
  name,
  date,
  circuit,
  raceStartUtc,
}: {
  year: number;
  round: number;
  name: string;
  date: string;
  circuit: { slug: string; name: string; country?: string | null };
  /** Exact lights-out moment when known; otherwise only the date is shown. */
  raceStartUtc: string | null;
}) {
  return (
    <article aria-labelledby="next-race-h" className="flex h-full flex-col rounded-lg border border-line bg-surface p-5">
      <p className="text-xs font-bold uppercase tracking-wide text-accent">
        Next race, round {round}
      </p>
      <h2 id="next-race-h" className="mt-1 text-2xl font-extrabold tracking-tight">
        <Link href={roundHref(year, round)} className="hover:text-accent hover:underline">
          {name}
        </Link>
      </h2>
      <p className="mt-1 text-muted">
        <Link href={circuitHref(circuit.slug)} className="font-semibold hover:text-accent hover:underline">
          {circuit.name}
        </Link>
        {circuit.country ? `, ${circuit.country}` : ""}
      </p>
      <p className="timing mt-1 text-sm text-muted">{formatDate(date)}</p>
      <div className="mt-5">
        {raceStartUtc ? <Countdown target={raceStartUtc} /> : <p className="text-sm text-muted">Start time to be confirmed</p>}
      </div>
      <p className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-sm font-semibold">
        <Link href="/calendar" className="text-muted hover:text-accent hover:underline">
          Full calendar &rarr;
        </Link>
        <a href={icsHref(year, round)} className="text-muted hover:text-accent hover:underline">
          Add to calendar
        </a>
      </p>
    </article>
  );
}
