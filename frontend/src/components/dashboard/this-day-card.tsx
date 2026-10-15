import Link from "next/link";
import type { components } from "@/lib/api/client";
import { formatDate } from "@/lib/format";
import { roundHref } from "@/lib/routes";
import { DriverLink } from "@/components/ui/entity-links";

type ThisDay = components["schemas"]["ThisDay"];

export function ThisDayCard({ item }: { item: ThisDay }) {
  return (
    <section aria-labelledby="this-day-h" className="self-start rounded-xl bg-surface p-6">
      <h2 id="this-day-h" className="text-sm font-bold text-accent">
        This day in F1
      </h2>
      <p className="timing mt-1 text-sm text-muted">{formatDate(item.date)}</p>
      <p className="heading mt-3 max-w-[34ch] text-2xl">
        <DriverLink slug={item.driver.slug} name={item.driver.name} /> won the{" "}
        {item.round != null ? (
          <Link href={roundHref(item.year, item.round)} className="underline underline-offset-4 hover:text-accent">
            {item.year} {item.race}
          </Link>
        ) : (
          <span>
            {item.year} {item.race}
          </span>
        )}{" "}
        for {item.team.name}.
      </p>
    </section>
  );
}
