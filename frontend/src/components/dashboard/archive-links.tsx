import Link from "next/link";
import { CATALOG_LINKS } from "@/lib/nav";

/** Ways into the archive: every list in the catalog, each with what it holds. */
export function ArchiveLinks() {
  return (
    <section aria-labelledby="archive-h">
      <p className="text-sm font-bold text-accent">The archive</p>
      <h2 id="archive-h" className="heading mb-5 mt-2 text-3xl sm:text-4xl">
        Every race since 1950
      </h2>
      <ul className="border-t border-line">
        {CATALOG_LINKS.map((l) => (
          <li key={l.href} className="border-b border-line">
            <Link href={l.href} className="t-fast group flex items-baseline justify-between gap-4 py-3.5 hover:text-accent">
              <span className="font-bold underline-offset-4 group-hover:underline">{l.label}</span>
              <span className="text-sm text-muted">{l.hint}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
