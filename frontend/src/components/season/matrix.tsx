import type { CSSProperties } from "react";
import type { components } from "@/lib/api/client";
import { formatPoints } from "@/lib/format";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { DriverLink, TeamDot } from "@/components/ui/entity-links";
import { Dash } from "@/components/ui/value";
import { getSeasonMatrix } from "./data";

type S = components["schemas"];
type Matrix = S["Matrix"];
type Category = S["MatrixCell"]["category"];

/**
 * Colour is never the only carrier: every category has its own symbol and the cell text is the
 * position. Backgrounds mix theme tokens, so they follow the light and dark themes.
 */
export const CATEGORY: Record<Category, { label: string; symbol: string; style: CSSProperties }> = {
  win: {
    label: "Win",
    symbol: "★",
    style: { backgroundColor: "color-mix(in srgb, var(--accent) 45%, var(--surface))", fontWeight: 800 },
  },
  podium: {
    label: "Podium",
    symbol: "▲",
    style: { backgroundColor: "color-mix(in srgb, var(--accent) 22%, var(--surface))", fontWeight: 700 },
  },
  points: {
    label: "Points finish",
    symbol: "●",
    style: { backgroundColor: "color-mix(in srgb, var(--fg-muted) 22%, var(--surface))" },
  },
  no_points: { label: "Finished outside the points", symbol: "○", style: {} },
  dnf: {
    label: "Did not finish",
    symbol: "✕",
    style: { backgroundColor: "color-mix(in srgb, var(--danger) 22%, var(--surface))" },
  },
};

const ORDER: Category[] = ["win", "podium", "points", "no_points", "dnf"];

export function describeCell(cell: S["MatrixCell"] | null): { text: string; label: string } {
  if (cell === null) return { text: "", label: "Did not take part" };
  const meta = CATEGORY[cell.category];
  const text = cell.position !== null ? String(cell.position) : "DNF";
  const label = cell.position !== null ? `${meta.label}, position ${cell.position}` : meta.label;
  return { text, label };
}

/** Async section for the season page: fetches itself, so a failure stays inside this section. */
export async function SeasonMatrixSection({ year }: { year: number }) {
  let matrix: Matrix | null;
  try {
    matrix = await getSeasonMatrix(year);
  } catch {
    return <ErrorState title="Could not load the results matrix" description="The calendar above is still available." />;
  }
  return <SeasonMatrix matrix={matrix} />;
}

export function SeasonMatrix({ matrix }: { matrix: Matrix | null }) {
  if (!matrix || matrix.rounds.length === 0 || matrix.drivers.length === 0) {
    return (
      <EmptyState title="No results yet" description="The grid fills in as soon as race results are imported for this season." />
    );
  }
  return (
    <div>
      <ul aria-label="Legend" className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-sm">
        {ORDER.map((c) => (
          <li key={c} className="flex items-center gap-1.5">
            <span
              aria-hidden="true"
              className="timing grid size-6 place-items-center rounded border border-line text-xs"
              style={CATEGORY[c].style}
            >
              {CATEGORY[c].symbol}
            </span>
            {CATEGORY[c].label}
          </li>
        ))}
        <li className="flex items-center gap-1.5">
          <span aria-hidden="true" className="grid size-6 place-items-center rounded border border-line text-xs text-muted">
            &mdash;
          </span>
          Did not take part
        </li>
      </ul>
      <div className="overflow-x-auto rounded-lg border border-line bg-surface" tabIndex={0} role="region" aria-label={`${matrix.year} results matrix, scrolls horizontally`}>
        <table className="border-collapse text-sm">
          <caption className="sr-only">
            {matrix.year} race results by driver and round. Each cell shows the finishing position and a symbol for the category.
          </caption>
          <thead>
            <tr>
              <th
                scope="col"
                className="sticky left-0 z-10 min-w-44 border-b border-r border-line bg-surface-2 px-3 py-2 text-left text-xs font-bold uppercase tracking-wide text-muted"
              >
                Driver
              </th>
              {matrix.rounds.map((r) => (
                <th
                  key={r.round}
                  scope="col"
                  title={r.name}
                  className="timing border-b border-line bg-surface-2 px-1 py-2 text-center text-xs font-bold text-muted"
                >
                  <span aria-hidden="true">R{r.round}</span>
                  <span className="sr-only">
                    Round {r.round}, {r.name}
                  </span>
                </th>
              ))}
              <th scope="col" className="border-b border-l border-line bg-surface-2 px-3 py-2 text-right text-xs font-bold uppercase tracking-wide text-muted">
                Points
              </th>
            </tr>
          </thead>
          <tbody>
            {matrix.drivers.map((d) => (
              <tr key={d.slug} className="border-b border-line last:border-b-0">
                <th
                  scope="row"
                  className="sticky left-0 z-10 whitespace-nowrap border-r border-line bg-surface px-3 py-1.5 text-left font-normal"
                >
                  <span className="flex items-center gap-2">
                    <span className="timing w-5 text-right text-xs text-muted">{d.position ?? <Dash />}</span>
                    <TeamDot color={d.team.color} />
                    <DriverLink slug={d.slug} name={d.name} />
                  </span>
                </th>
                {matrix.rounds.map((r, i) => {
                  const cell = d.cells[i] ?? null;
                  const { text, label } = describeCell(cell);
                  const full = `${d.name}, ${r.name}: ${label}`;
                  return (
                    <td
                      key={r.round}
                      title={full}
                      style={cell ? CATEGORY[cell.category].style : undefined}
                      className="timing h-9 min-w-11 border-l border-line px-1 text-center"
                    >
                      {cell ? (
                        <>
                          <span aria-hidden="true">
                            <span className="mr-0.5 text-[0.6rem]">{CATEGORY[cell.category].symbol}</span>
                            {text}
                          </span>
                          <span className="sr-only">{full}</span>
                        </>
                      ) : (
                        <>
                          <span aria-hidden="true" className="text-muted">
                            &mdash;
                          </span>
                          <span className="sr-only">{full}</span>
                        </>
                      )}
                    </td>
                  );
                })}
                <td className="timing border-l border-line px-3 text-right font-bold">{formatPoints(d.points) ?? <Dash />}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
