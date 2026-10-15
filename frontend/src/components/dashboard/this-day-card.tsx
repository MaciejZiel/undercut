import Link from "next/link";
import type { components } from "@/lib/api/client";
import { formatDate } from "@/lib/format";
import { roundHref } from "@/lib/routes";
import { DriverLink } from "@/components/ui/entity-links";

type ThisDay = components["schemas"]["ThisDay"];

export function ThisDayCard({ item }: { item: ThisDay }) {
  return (
    <section aria-labelledby="this-day-h" className="rounded-lg border border-line bg-surface p-5">
      <h2 id="this-day-h" className="text-xs font-bold uppercase tracking-wide text-accent">
        This day in F1
      </h2>
      <p className="timing mt-1 text-sm text-muted">{formatDate(item.date)}</p>
      <p className="mt-2 text-lg">
        <DriverLink slug={item.driver.slug} name={item.driver.name} /> won the{" "}
        {item.round != null ? (
          <Link href={roundHref(item.year, item.round)} className="font-semibold hover:text-accent hover:underline">
            {item.year} {item.race}
          </Link>
        ) : (
          <span className="font-semibold">
            {item.year} {item.race}
          </span>
        )}{" "}
        for {item.team.name}.
      </p>
    </section>
  );
}
