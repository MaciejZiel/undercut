import Link from "next/link";
import type { components } from "@/lib/api/client";
import { circuitHref, roundHref } from "@/lib/routes";
import { formatDate, formatInteger, formatLapTime, formatLength } from "@/lib/format";
import { icsHref } from "@/components/calendar/time";
import { DownloadIcon } from "@/components/ui/icons";
import { TrackOutline } from "@/components/catalog/track-outline";
import { Countdown } from "./countdown";
import { WeekendSchedule } from "./weekend-schedule";

type Session = components["schemas"]["CalendarSession"];
type CircuitDetail = components["schemas"]["CircuitDetail"];

/** The next race weekend: the name, the place with a photograph, and the schedule in the viewer's time zone. */
export function NextRaceCard({
  year,
  round,
  name,
  date,
  circuit,
  raceStartUtc,
  sessions,
  circuitDetail = null,
}: {
  year: number;
  round: number;
  name: string;
  date?: string;
  circuit: { slug: string; name: string; country?: string | null; locality?: string | null };
  /** Exact lights-out moment when known; otherwise only the date is shown. */
  raceStartUtc: string | null;
  sessions: Session[];
  /** Drawing and records of the circuit, when known. Nothing is drawn without an outline. */
  circuitDetail?: CircuitDetail | null;
}) {
  const place = [circuit.locality, circuit.country].filter(Boolean).join(", ");
  return (
    <article aria-labelledby="next-race-h" className="grid grid-cols-1 gap-x-10 gap-y-8 lg:grid-cols-[minmax(0,1.88fr)_minmax(20rem,1fr)] lg:gap-x-12">
      <div className="flex flex-col">
        <p className="flex flex-wrap items-baseline gap-x-4 text-sm font-bold text-accent">
          Next race
          <span className="font-medium text-muted">
            Round {round} · {year}
          </span>
        </p>
        <h2 id="next-race-h" className="display mt-3 text-[2.75rem] sm:text-6xl">
          <Link href={roundHref(year, round)} className="underline-offset-8 hover:underline">
            {name}
          </Link>
        </h2>
        <p className="mt-4 flex flex-wrap justify-between gap-x-6 gap-y-1 text-sm text-muted">
          <span>
            <Link href={circuitHref(circuit.slug)} className="font-semibold text-fg underline-offset-4 hover:text-accent hover:underline">
              {circuit.name}
            </Link>
            {place ? `, ${place}` : ""}
          </span>
          {date && <span className="whitespace-nowrap">Race day {formatDate(date)}</span>}
        </p>
        {circuitDetail?.outline && (
          <TrackOutline outline={circuitDetail.outline} name={circuit.name} className="mt-6 max-h-[22rem] w-full" />
        )}
        <CircuitFacts detail={circuitDetail} />
      </div>
      <aside aria-labelledby="weekend-h" className="flex flex-col rounded-xl bg-surface p-6 sm:p-7">
        <h3 id="weekend-h" className="heading text-xl sm:text-[1.375rem]">
          Race weekend
        </h3>
        <div className="mt-4 min-h-[3.25rem] border-b border-line pb-4">
          {raceStartUtc ? (
            <>
              <p className="mb-1 text-xs font-semibold text-muted">Lights out in</p>
              <Countdown target={raceStartUtc} />
            </>
          ) : (
            <p className="text-sm text-muted">Start time to be confirmed</p>
          )}
        </div>
        <WeekendSchedule sessions={sessions} />
        <a
          href={icsHref(year, round)}
          className="t-fast mt-6 inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-accent px-5 py-2.5 text-sm font-bold text-accent-fg hover:bg-accent-hover"
        >
          <DownloadIcon aria-hidden="true" />
          Add the weekend to my calendar
        </a>
        <Link href="/calendar" className="mt-4 text-center text-sm font-bold text-accent underline underline-offset-4 hover:no-underline">
          Full calendar
        </Link>
      </aside>
    </article>
  );
}

function CircuitFacts({ detail }: { detail: CircuitDetail | null }) {
  if (!detail) return null;
  const record = formatLapTime(detail.lap_record_ms);
  const length = formatLength(detail.length_m);
  const items = [
    record && { label: "Lap record", value: record, note: [detail.lap_record_driver, detail.lap_record_year].filter(Boolean).join(", ") },
    length && { label: "Lap length", value: `${detail.length_is_estimate ? "≈ " : ""}${length}` },
    detail.gp_count > 0 && { label: "Grands Prix here", value: formatInteger(detail.gp_count) ?? "" },
  ].filter((i): i is { label: string; value: string; note?: string } => Boolean(i));
  if (items.length === 0) return null;
  return (
    <dl aria-label={`${detail.name} facts`} className="mt-5 flex flex-wrap gap-x-10 gap-y-4 border-t border-line pt-4">
      {items.map((i) => (
        <div key={i.label} className="flex flex-col-reverse justify-end">
          <dt className="mt-0.5 text-[0.8125rem] font-semibold text-muted">
            {i.label}
            {i.note ? ` · ${i.note}` : ""}
          </dt>
          <dd className="numeral text-2xl">{i.value}</dd>
        </div>
      ))}
    </dl>
  );
}
