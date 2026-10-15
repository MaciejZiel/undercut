import type React from "react";
import Link from "next/link";
import type { components } from "@/lib/api/client";
import { formatDate, formatInteger } from "@/lib/format";
import { CircuitLink, ConstructorLink, DriverLink, Nationality, RoundLink } from "@/components/ui/entity-links";
import { DataTable, RowTh, SortTh, Td, Th, Tr } from "@/components/ui/data-table";
import { orDash } from "@/components/ui/value";

type S = components["schemas"];

export function CircuitsTable({
  circuits,
  ordering,
  params,
}: {
  circuits: S["CircuitList"][];
  ordering: string;
  params: Record<string, string | number | undefined>;
}) {
  const sort = { ordering, params, path: "/circuits" };
  return (
    <DataTable caption="Circuits" minWidth="38rem">
      <thead>
        <tr>
          <SortTh label="Circuit" field="name" {...sort} />
          <Th>Location</Th>
          <SortTh label="Country" field="country" {...sort} />
          <SortTh label="Grands Prix" field="gp_count" numeric {...sort} />
          <SortTh label="Last GP" field="last_gp_date" numeric {...sort} />
        </tr>
      </thead>
      <tbody>
        {circuits.map((c) => (
          <Tr key={c.slug}>
            <RowTh>
              <CircuitLink slug={c.slug} name={c.name} />
            </RowTh>
            <Td>{orDash(c.locality)}</Td>
            <Td>
              <Nationality value={c.country} />
            </Td>
            <Td align="right">{orDash(formatInteger(c.gp_count))}</Td>
            <Td align="right" className="whitespace-nowrap">
              {orDash(formatDate(c.last_gp_date))}
            </Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}

export function CircuitWinnersTable({ winners }: { winners: S["CircuitWinner"][] }) {
  return (
    <DataTable caption="Winners" minWidth="36rem">
      <thead>
        <tr>
          <Th>Year</Th>
          <Th>Grand Prix</Th>
          <Th>Driver</Th>
          <Th>Team</Th>
        </tr>
      </thead>
      <tbody>
        {winners.map((w) => (
          <Tr key={`${w.year}-${w.round}-${w.round_name}`}>
            <RowTh className="timing font-semibold">
              <Link href={`/seasons/${w.year}`} className="hover:text-accent hover:underline">
                {w.year}
              </Link>
            </RowTh>
            <Td>
              {w.round != null ? (
                <RoundLink year={w.year} round={w.round} name={w.round_name} />
              ) : (
                w.round_name
              )}
            </Td>
            <Td>
              <DriverLink slug={w.driver.slug} name={w.driver.name} />
            </Td>
            <Td>
              <ConstructorLink {...w.team} />
            </Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}

export function MostWinsList({
  title,
  items,
}: {
  title: string;
  items: { key: string; node: React.ReactNode; wins: number }[];
}) {
  return (
    <section aria-label={title} className="rounded-lg border border-line bg-surface p-4">
      <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">{title}</h3>
      {items.length === 0 ? (
        <p className="text-muted">{orDash(null)}</p>
      ) : (
        <ol className="space-y-1.5">
          {items.map((i) => (
            <li key={i.key} className="flex items-baseline justify-between gap-3">
              {i.node}
              <span className="timing font-bold">
                {i.wins} <span className="sr-only">wins</span>
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
