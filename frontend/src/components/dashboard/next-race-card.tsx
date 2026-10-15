import Link from "next/link";
import type { components } from "@/lib/api/client";
import { circuitHref, roundHref } from "@/lib/routes";
import { formatInteger, formatLapTime, formatLength } from "@/lib/format";
import { AddToCalendar } from "@/components/calendar/add-to-calendar";
import { TrackOutline } from "@/components/catalog/track-outline";
import { Countdown } from "./countdown";
import { WeekendSchedule } from "./weekend-schedule";

type Session = components["schemas"]["CalendarSession"];
type CircuitDetail = components["schemas"]["CircuitDetail"];

const stagger = (i: number) => ({ "--i": i }) as React.CSSProperties;

/** "25 OCT" from an ISO date, always UTC so the server and the browser agree. */
function dayMonth(iso: string): string {
  const d = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return "";
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" }).format(d).toUpperCase();
}

/** The next race weekend: the place set huge, the date, the clock and every session in the viewer's time zone. */
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
  // The headline is the place people say ("Austin"), the race name sits under it.
  const headline = circuit.locality ?? name.replace(/ Grand Prix.*$/, "");
  return (
    <article aria-labelledby="next-race-h" className="grid grid-cols-1 border-b border-fg lg:grid-cols-[minmax(0,1fr)_23.5rem]">
      <div className="relative flex flex-col overflow-hidden py-7 lg:pr-9">
        <div className="flex flex-wrap items-center gap-3">
          <span className="bg-accent px-2 py-1 text-[0.625rem] font-bold tracking-[0.1em] text-accent-fg">UP NEXT</span>
          <span className="eyebrow">
            Round {round} / {year}
          </span>
        </div>
        <span
          aria-hidden="true"
          className="numeral pointer-events-none absolute right-0 top-14 hidden select-none text-[clamp(6rem,15vw,9.5rem)] tracking-[-0.07em] text-ghost sm:block lg:right-9"
        >
          {round}
        </span>
        {circuitDetail?.outline && (
          <TrackOutline
            outline={circuitDetail.outline}
            name={circuit.name}
            lapMs={circuitDetail.lap_record_ms}
            className="absolute bottom-24 right-4 hidden max-h-[17rem] w-[22rem] sm:block lg:right-10"
          />
        )}
        <h2 id="next-race-h" className="display relative mt-5 text-[clamp(3.5rem,11vw,6.75rem)]">
          <Link href={roundHref(year, round)} className="hover:text-accent">
            {headline}
          </Link>
          .
        </h2>
        <p className="mt-2 text-lg font-semibold">{name}</p>
        <div className="mt-7 flex flex-wrap items-end gap-x-8 gap-y-4">
          {date && (
            <div>
              <p className="eyebrow mb-1">Race day</p>
              <p className="numeral text-[1.75rem]">{dayMonth(date)}</p>
            </div>
          )}
          <p className="text-[0.8125rem] leading-relaxed">
            <Link href={circuitHref(circuit.slug)} className="font-semibold underline-offset-4 hover:text-accent hover:underline">
              {circuit.name}
            </Link>
            <br />
            <span className="text-muted">{place}</span>
          </p>
          <Link
            href={roundHref(year, round)}
            className="t-fast ml-auto border-b-2 border-accent pb-1.5 text-[0.8125rem] font-bold hover:text-accent"
          >
            Explore the weekend ↗
          </Link>
        </div>
        <div className="mt-auto pt-8">
          <CircuitFacts detail={circuitDetail} />
        </div>
      </div>
      <aside
        aria-labelledby="weekend-h"
        className="rise border-t border-fg py-7 lg:border-l lg:border-t-0 lg:pl-7"
        style={stagger(2)}
      >
        <h3 id="weekend-h" className="eyebrow">
          Lights out in
        </h3>
        <div className="mt-3 min-h-[4.5rem]">
          {raceStartUtc ? <Countdown target={raceStartUtc} clock /> : <p className="text-sm text-muted">Start time to be confirmed</p>}
        </div>
        <div className="mt-5">
          <WeekendSchedule sessions={sessions} />
        </div>
        <div className="mt-2">
          <div className="border-b border-line py-2.5">
            <AddToCalendar year={year} round={round} label="Add the weekend to my calendar" />
          </div>
          <Link href="/calendar" className="t-fast flex items-baseline justify-between gap-3 border-b border-line py-2.5 text-[0.8125rem] hover:text-accent">
            <b>Full schedule</b>
            <span>View calendar ↗</span>
          </Link>
        </div>
        <Link
          href="/predict"
          className="t-fast mt-5 flex items-center justify-between bg-fg px-4 py-3.5 text-[0.8125rem] font-bold text-bg hover:-translate-y-px hover:bg-accent hover:text-accent-fg"
        >
          Make your podium picks
          <span aria-hidden="true">↗</span>
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
    <dl aria-label={`${detail.name} facts`} className="mt-7 flex flex-wrap gap-x-10 gap-y-3 border-t border-line pt-4">
      {items.map((i) => (
        <div key={i.label} className="flex flex-col-reverse justify-end">
          <dt className="eyebrow mt-1">
            {i.label}
            {i.note ? ` / ${i.note}` : ""}
          </dt>
          <dd className="numeral text-[1.375rem]">{i.value}</dd>
        </div>
      ))}
    </dl>
  );
}
