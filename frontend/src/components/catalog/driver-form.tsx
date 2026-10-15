import { describeCell, CATEGORY } from "@/components/season/matrix";
import { getSeasonMatrix } from "@/components/season/data";

/**
 * One driver's row of the season results matrix: how the season has gone, round by round, in the
 * same cells as the season page. Renders nothing when the season has no matrix or the driver is not in it.
 */
export async function DriverFormRow({ slug, year }: { slug: string; year: number }) {
  let matrix;
  try {
    matrix = await getSeasonMatrix(year);
  } catch {
    return null;
  }
  if (!matrix) return null;
  const row = matrix.drivers.find((d) => d.slug === slug);
  if (!row || row.cells.every((c) => c === null)) return null;
  return (
    <section aria-labelledby="form-h" className="mb-10">
      <h2 id="form-h" className="mb-3 heading text-xl sm:text-[1.375rem]">
        {year} round by round
      </h2>
      <ol aria-label={`${row.name} results in ${year}`} className="flex flex-wrap gap-1">
        {matrix.rounds.map((r, i) => {
          const cell = row.cells[i] ?? null;
          const { text, label } = describeCell(cell);
          const full = `${r.name}: ${label}`;
          return (
            <li key={r.round} className="w-11 text-center" title={full}>
              <span
                style={cell ? CATEGORY[cell.category].style : undefined}
                className="timing grid h-9 place-items-center whitespace-nowrap rounded-sm border border-line text-sm"
              >
                <span aria-hidden="true">{cell ? text : ""}</span>
                <span className="sr-only">{full}</span>
              </span>
              <span aria-hidden="true" className="mt-1 block text-[0.6875rem] text-muted">
                R{r.round}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
