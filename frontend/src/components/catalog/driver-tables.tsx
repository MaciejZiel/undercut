import Link from "next/link";
import { seasonHref } from "@/lib/routes";
import type { components } from "@/lib/api/client";
import { fullName, formatDate, formatInteger, formatPoints, formatPosition } from "@/lib/format";
import { ConstructorLink, DriverLink, Nationality, RoundLink } from "@/components/ui/entity-links";
import { DataTable, RowTh, SortTh, Td, Th, Tr } from "@/components/ui/data-table";
import { Dash, orDash } from "@/components/ui/value";

type S = components["schemas"];

export function DriversTable({
  drivers,
  ordering,
  params,
  path = "/drivers",
}: {
  drivers: S["DriverList"][];
  ordering: string;
  params: Record<string, string | number | undefined>;
  path?: string;
}) {
  const sort = { ordering, params, path };
  return (
    <DataTable caption="Drivers" minWidth="44rem">
      <thead>
        <tr>
          <Th align="right">No.</Th>
          <SortTh label="Driver" field="family_name" {...sort} />
          <Th>Nationality</Th>
          <Th>Team</Th>
          <SortTh label="Starts" field="starts" numeric {...sort} />
          <SortTh label="Wins" field="wins" numeric {...sort} />
          <SortTh label="Titles" field="titles" numeric {...sort} />
        </tr>
      </thead>
      <tbody>
        {drivers.map((d) => (
          <Tr key={d.slug}>
            <Td align="right" className="timing text-muted">
              {orDash(d.number)}
            </Td>
            <RowTh>
              <DriverLink slug={d.slug} name={fullName(d)} />
            </RowTh>
            <Td>
              <Nationality value={d.nationality} />
            </Td>
            <Td>{d.team ? <ConstructorLink {...d.team} /> : <Dash />}</Td>
            <Td align="right">{orDash(formatInteger(d.starts))}</Td>
            <Td align="right">{orDash(formatInteger(d.wins))}</Td>
            <Td align="right">{orDash(formatInteger(d.titles))}</Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}

export function DriverSeasonsTable({ seasons }: { seasons: S["DriverSeason"][] }) {
  return (
    <DataTable caption="Seasons" minWidth="32rem">
      <thead>
        <tr>
          <Th>Year</Th>
          <Th>Team</Th>
          <Th align="right">Position</Th>
          <Th align="right">Points</Th>
          <Th align="right">Wins</Th>
        </tr>
      </thead>
      <tbody>
        {seasons.map((s) => (
          <Tr key={s.year}>
            <RowTh className="timing font-semibold">
              <Link href={seasonHref(s.year)} className="hover:text-accent hover:underline">
                {s.year}
              </Link>
            </RowTh>
            <Td>
              {s.teams.length === 0 ? (
                <Dash />
              ) : (
                <span className="flex flex-wrap gap-x-4 gap-y-1">
                  {s.teams.map((t) => (
                    <ConstructorLink key={t.slug} {...t} />
                  ))}
                </span>
              )}
            </Td>
            <Td align="right">{orDash(s.championship_position, "Not available yet")}</Td>
            <Td align="right">{orDash(formatPoints(s.points))}</Td>
            <Td align="right">{orDash(formatInteger(s.wins))}</Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}

export function DriverLastResultsTable({ results }: { results: S["DriverResult"][] }) {
  return (
    <DataTable caption="Last results" minWidth="38rem">
      <thead>
        <tr>
          <Th>Race</Th>
          <Th>Date</Th>
          <Th>Team</Th>
          <Th align="right">Grid</Th>
          <Th align="right">Finish</Th>
          <Th>Status</Th>
          <Th align="right">Points</Th>
        </tr>
      </thead>
      <tbody>
        {results.map((r) => (
          <Tr key={`${r.year}-${r.round}-${r.round_name}`}>
            <RowTh>
              {r.round != null ? (
                <RoundLink year={r.year} round={r.round} name={`${r.year} ${r.round_name}`} />
              ) : (
                <span>
                  {r.year} {r.round_name}
                </span>
              )}
            </RowTh>
            <Td className="whitespace-nowrap text-muted">{orDash(formatDate(r.date))}</Td>
            <Td>
              <ConstructorLink {...r.team} />
            </Td>
            <Td align="right">{orDash(r.grid)}</Td>
            <Td align="right" className="font-semibold">
              {orDash(formatPosition(r.position, r.position_text))}
            </Td>
            <Td>{orDash(r.status)}</Td>
            <Td align="right">{orDash(formatPoints(r.points))}</Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}
