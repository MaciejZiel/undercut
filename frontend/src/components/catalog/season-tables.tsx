import Link from "next/link";
import type { components } from "@/lib/api/client";
import { formatDayMonth } from "@/lib/format";
import { seasonHref } from "@/lib/routes";
import { Badge, CircuitLink, ConstructorLink, DriverLink, RoundLink } from "@/components/ui/entity-links";
import { DataTable, RowTh, Td, Th, Tr } from "@/components/ui/data-table";
import { Dash, orDash } from "@/components/ui/value";

type S = components["schemas"];

export function SeasonsTable({ seasons }: { seasons: S["SeasonList"][] }) {
  return (
    <DataTable caption="Seasons" minWidth="40rem">
      <thead>
        <tr>
          <Th>Season</Th>
          <Th>Drivers&apos; champion</Th>
          <Th>Constructors&apos; champion</Th>
          <Th align="right">Rounds</Th>
          <Th align="right">Sprints</Th>
        </tr>
      </thead>
      <tbody>
        {seasons.map((s) => (
          <Tr key={s.year}>
            <RowTh className="timing">
              <Link href={seasonHref(s.year)} className="font-bold hover:text-accent hover:underline">
                {s.year}
              </Link>
              {s.name && s.name !== String(s.year) && <span className="ml-2 text-muted">{s.name}</span>}
            </RowTh>
            <Td>
              {s.driver_champion ? (
                <DriverLink slug={s.driver_champion.slug} name={s.driver_champion.name} />
              ) : (
                <Dash label="Not available yet" />
              )}
            </Td>
            <Td>
              {s.constructor_champion ? (
                <ConstructorLink {...s.constructor_champion} />
              ) : (
                <Dash label="Not available yet" />
              )}
            </Td>
            <Td align="right">
              {s.rounds_count}
              {s.cancelled_rounds > 0 && (
                <span className="ml-1 text-muted" title={`${s.cancelled_rounds} cancelled`}>
                  ({s.cancelled_rounds} cancelled)
                </span>
              )}
            </Td>
            <Td align="right">{s.sprint_rounds}</Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}

export function CalendarTable({
  year,
  rounds,
  today,
}: {
  year: number;
  rounds: S["CalendarRound"][];
  /** ISO date used to tell upcoming rounds from rounds without data. */
  today: string;
}) {
  return (
    <DataTable caption={`${year} calendar`} minWidth="44rem">
      <thead>
        <tr>
          <Th align="right">Round</Th>
          <Th>Date</Th>
          <Th>Grand Prix</Th>
          <Th>Circuit</Th>
          <Th>Winner</Th>
        </tr>
      </thead>
      <tbody>
        {rounds.map((r, i) => (
          <Tr key={`${r.round ?? "x"}-${i}`} muted={r.is_cancelled}>
            <Td align="right" className="timing text-muted">
              {orDash(r.round)}
            </Td>
            <Td className="timing whitespace-nowrap">{orDash(formatDayMonth(r.date))}</Td>
            <RowTh>
              <span className="flex flex-wrap items-center gap-2">
                {r.round != null && !r.is_cancelled ? (
                  <RoundLink year={year} round={r.round} name={r.name} />
                ) : (
                  <span className={r.is_cancelled ? "line-through" : "font-semibold"}>{r.name}</span>
                )}
                {r.is_cancelled && <Badge tone="danger">Cancelled</Badge>}
                {r.has_sprint && <Badge>Sprint</Badge>}
              </span>
            </RowTh>
            <Td>
              <CircuitLink slug={r.circuit.slug} name={r.circuit.name} />
            </Td>
            <Td>
              {r.winner ? (
                <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <DriverLink slug={r.winner.driver.slug} name={r.winner.driver.name} />
                  <ConstructorLink {...r.winner.team} />
                </span>
              ) : r.is_cancelled ? (
                <Dash label="No winner: round cancelled" />
              ) : r.date.slice(0, 10) >= today ? (
                <span className="text-muted">Upcoming</span>
              ) : (
                <Dash label="No result yet" />
              )}
            </Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}
