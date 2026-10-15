import Link from "next/link";
import { formatInteger } from "@/lib/format";

const link = "font-bold text-accent underline underline-offset-4 hover:no-underline";

/** The way into the archive: one sentence with the four lists linked in it, and what the archive holds. */
export function ArchiveLinks({ counts }: { counts?: { seasons: number; races: number; drivers: number } | null }) {
  return (
    <section aria-labelledby="archive-h">
      <p className="text-sm font-bold text-accent">The archive</p>
      <h2 id="archive-h" className="heading mb-4 mt-2 text-xl sm:text-[1.375rem]">
        Every race since 1950
      </h2>
      <p className="max-w-[34ch] text-lg leading-snug">
        Every{" "}
        <Link href="/drivers" className={link}>
          driver
        </Link>
        ,{" "}
        <Link href="/constructors" className={link}>
          constructor
        </Link>
        ,{" "}
        <Link href="/circuits" className={link}>
          circuit
        </Link>{" "}
        and{" "}
        <Link href="/seasons" className={link}>
          season
        </Link>{" "}
        since 1950.
      </p>
      {counts && (
        <p className="mt-3 text-sm tabular-nums text-muted">
          {formatInteger(counts.seasons)} seasons · {formatInteger(counts.races)} races · {formatInteger(counts.drivers)} drivers
        </p>
      )}
    </section>
  );
}
