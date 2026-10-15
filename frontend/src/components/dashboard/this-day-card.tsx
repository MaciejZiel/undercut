import Link from "next/link";
import type { components } from "@/lib/api/client";
import { roundHref } from "@/lib/routes";
import { DriverLink } from "@/components/ui/entity-links";

type ThisDay = components["schemas"]["ThisDay"];

/** A race won on today's date in an earlier year: the year large in red, the sentence beside it. */
export function ThisDayCard({ item }: { item: ThisDay }) {
  return (
    <section aria-labelledby="this-day-h" className="flex flex-col items-start gap-x-6 gap-y-2 py-6 sm:flex-row sm:items-center lg:pr-8">
      <span aria-hidden="true" className="numeral shrink-0 text-[3.25rem] tracking-[-0.06em] text-accent sm:text-[3.625rem]">
        {item.year}
      </span>
      <div>
        <h2 id="this-day-h" className="eyebrow mb-1.5">
          On this day
        </h2>
        <p className="max-w-[36ch] text-[0.9375rem] leading-relaxed">
          <DriverLink slug={item.driver.slug} name={item.driver.name} /> won the{" "}
          {item.round != null ? (
            <Link href={roundHref(item.year, item.round)} className="font-bold underline decoration-accent decoration-2 underline-offset-4 hover:text-accent">
              {item.year} {item.race}
            </Link>
          ) : (
            <b>
              {item.year} {item.race}
            </b>
          )}{" "}
          for {item.team.name}.
        </p>
      </div>
    </section>
  );
}
