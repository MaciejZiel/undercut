import Link from "next/link";
import type { components } from "@/lib/api/client";
import { formatInteger, formatPoints } from "@/lib/format";
import { ConstructorLink, DriverLink, Nationality } from "@/components/ui/entity-links";
import { DataTable, RowTh, SortTh, Td, Th, Tr } from "@/components/ui/data-table";
import { Dash, orDash } from "@/components/ui/value";
import { seasonHref } from "@/lib/routes";

type S = components["schemas"];

export function ConstructorsTable({
  constructors,
  ordering,
  params,
}: {
  constructors: S["ConstructorList"][];
  ordering: string;
  params: Record<string, string | number | undefined>;
}) {
  const sort = { ordering, params, path: "/constructors" };
  return (
    <DataTable caption="Constructors" minWidth="36rem">
      <thead>
        <tr>
          <SortTh label="Constructor" field="name" {...sort} />
          <Th>Nationality</Th>
          <SortTh label="Starts" field="starts" numeric {...sort} />
          <SortTh label="Wins" field="wins" numeric {...sort} />
          <Th align="right">Titles</Th>
        </tr>
      </thead>
      <tbody>
        {constructors.map((c) => (
          <Tr key={c.slug}>
            <RowTh>
              <ConstructorLink slug={c.slug} name={c.name} stretch />
            </RowTh>
            <Td>
              <Nationality value={c.nationality} />
            </Td>
            <Td align="right">{orDash(formatInteger(c.starts))}</Td>
            <Td align="right">{orDash(formatInteger(c.wins))}</Td>
            <Td align="right">{orDash(formatInteger(c.titles), "Not available yet")}</Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}

export function ConstructorSeasonsTable({ seasons }: { seasons: S["ConstructorSeasonRow"][] }) {
  return (
    <DataTable caption="Seasons" minWidth="38rem">
      <thead>
        <tr>
          <Th>Year</Th>
          <Th align="right">Position</Th>
          <Th align="right">Points</Th>
          <Th align="right">Wins</Th>
          <Th>Drivers</Th>
        </tr>
      </thead>
      <tbody>
        {seasons.map((s) => (
          <Tr key={s.year}>
            <RowTh className="timing font-semibold">
              <Link href={seasonHref(s.year)} className="rowlink hover:text-accent hover:underline">
                {s.year}
              </Link>
            </RowTh>
            <Td align="right">{orDash(s.championship_position, "Not available yet")}</Td>
            <Td align="right">{orDash(formatPoints(s.points))}</Td>
            <Td align="right">{orDash(formatInteger(s.wins))}</Td>
            <Td>
              {s.drivers.length === 0 ? (
                <Dash />
              ) : (
                <span className="flex flex-wrap gap-x-4 gap-y-1">
                  {s.drivers.map((d) => (
                    <DriverLink key={d.slug} slug={d.slug} name={d.name} />
                  ))}
                </span>
              )}
            </Td>
          </Tr>
        ))}
      </tbody>
    </DataTable>
  );
}
