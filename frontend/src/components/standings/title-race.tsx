import { connection } from "next/server";
import type { components } from "@/lib/api/client";
import { formatInteger, formatPoints } from "@/lib/format";
import { parseIntParam, type SearchParams } from "@/lib/url";
import { DataTable, RowTh, Td, Th, Tr } from "@/components/ui/data-table";
import { Badge, DriverLink } from "@/components/ui/entity-links";
import { Dash } from "@/components/ui/value";
import { ErrorState } from "@/components/states/error-state";
import { getTitleRace } from "./title-race-data";

type TitleRace = components["schemas"]["TitleRace"];

/**
 * Title race panel of the drivers standings page. Shown only for the current season: when the
 * URL asks for another year (or a round in the past) nothing is rendered.
 */
export async function TitleRaceSection({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const sp = await searchParams;
  // The clock is read after the request-scoped searchParams, so this render is per request.
  await connection();
  const season = parseIntParam(sp.season, { min: 1950, max: 2100 });
  const afterRound = parseIntParam(sp.after_round, { min: 1, max: 100 });
  if (afterRound !== undefined) return null;
  if (season !== undefined && season !== new Date().getUTCFullYear()) return null;
  let race: TitleRace | null;
  try {
    race = await getTitleRace(season);
  } catch {
    return <ErrorState title="Could not load the title race" description="The standings table above is still available." />;
  }
  return race ? <TitleRacePanel race={race} /> : null;
}

export function TitleRacePanel({ race }: { race: TitleRace }) {
  // Nothing to say before the first standings exist.
  if (race.season === null) return null;
  const heading = `Title race ${race.season}`;
  return (
    <section aria-labelledby="title-race-h" className="mt-10">
      <h2 id="title-race-h" className="mb-1 heading text-xl sm:text-[1.375rem]">
        {heading}
      </h2>
      {race.decided && race.champion ? (
        <p className="mb-3 font-semibold" role="status">
          <DriverLink slug={race.champion.slug} name={race.champion.name} /> is the champion.
          {race.message ? ` ${race.message}.` : ""}
        </p>
      ) : (
        <p className="mb-3 text-sm text-muted">
          {race.rounds_remaining !== null ? (
            <>
              {race.rounds_remaining} {race.rounds_remaining === 1 ? "round" : "rounds"}
              {race.sprints_remaining ? ` and ${race.sprints_remaining} ${race.sprints_remaining === 1 ? "sprint" : "sprints"}` : ""} left
              {race.max_points_available !== null ? `, at most ${formatPoints(race.max_points_available)} points for one driver` : ""}.
            </>
          ) : (
            "Remaining rounds are not known."
          )}{" "}
          {race.eliminated > 0 ? `${formatInteger(race.eliminated)} drivers can no longer win the title.` : ""}
        </p>
      )}
      {race.contenders.length === 0 ? (
        <p className="text-sm text-muted">No driver is left in the title race.</p>
      ) : (
        <DataTable caption={`${heading}: drivers who can still win the championship`} minWidth="34rem">
          <thead>
            <tr>
              <Th className="w-12">Pos</Th>
              <Th>Driver</Th>
              <Th align="right">Points</Th>
              <Th align="right">Gap</Th>
              <Th align="right">Max possible</Th>
            </tr>
          </thead>
          <tbody>
            {race.contenders.map((c) => {
              const champion = race.champion?.id === c.entity.id;
              return (
                <Tr key={c.entity.id}>
                  <RowTh className="timing font-bold">{c.position ?? <Dash />}</RowTh>
                  <Td>
                    <DriverLink slug={c.entity.slug} name={c.entity.name} />
                    {champion && (
                      <span className="ml-2">
                        <Badge tone="accent">Champion</Badge>
                      </span>
                    )}
                    {!champion && c.tie_break_needed && <span className="ml-2 text-sm text-muted">Only on countback</span>}
                  </Td>
                  <Td align="right" className="timing font-bold">
                    {formatPoints(c.points) ?? <Dash />}
                  </Td>
                  <Td align="right" className="timing">
                    {c.gap_to_leader === 0 ? <Dash label="Leader, or level with the leader" /> : (formatPoints(c.gap_to_leader) ?? <Dash />)}
                  </Td>
                  <Td align="right" className="timing">
                    {formatPoints(c.max_points) ?? <Dash />}
                  </Td>
                </Tr>
              );
            })}
          </tbody>
        </DataTable>
      )}
    </section>
  );
}
