import type { components } from "@/lib/api/client";
import { DriverLink } from "@/components/ui/entity-links";

type RaceResult = components["schemas"]["RaceResult"];

/** The drivers who gained the most places between the grid and the flag; nothing is shown for a quiet race. */
export function BiggestMovers({ results }: { results: RaceResult[] }) {
  const movers = results
    .filter((r) => r.position != null && r.grid != null && r.grid > 0 && (r.position_change ?? 0) >= 5)
    .sort((a, b) => (b.position_change ?? 0) - (a.position_change ?? 0))
    .slice(0, 3);
  if (movers.length === 0) return null;
  return (
    <section aria-labelledby="movers-h" className="mt-10">
      <h3 id="movers-h" className="heading text-xl sm:text-[1.375rem]">
        Biggest gains
      </h3>
      <ul className="mt-3 border-t border-line">
        {movers.map((r) => (
          <li key={r.driver.slug} className="flex items-baseline gap-4 border-b border-line py-3">
            <span className="w-10 shrink-0 text-lg font-extrabold tabular-nums text-positive">
              +{r.position_change}
              <span className="sr-only"> places</span>
            </span>
            <span className="font-bold">
              <DriverLink slug={r.driver.slug} name={r.driver.name} />
            </span>
            <span className="ml-auto text-sm text-muted tabular-nums">
              P{r.grid} to P{r.position}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
