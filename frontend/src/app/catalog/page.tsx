import { Suspense } from "react";
import Link from "next/link";
import { ThisDaySection } from "@/components/dashboard/sections";
import { PageHeader } from "@/components/ui/page-header";
import { ARCHIVE_LINKS } from "@/lib/nav";

export const metadata = { title: "Archive" };

export default function CatalogPage() {
  return (
    <>
      <PageHeader title="Archive" description="Browse the sport by driver, team, track or year." />
      <ul className="max-w-3xl border-t border-line">
        {ARCHIVE_LINKS.map((l) => (
          <li key={l.href} className="border-b border-line">
            <Link href={l.href} className="t-fast group flex items-baseline justify-between gap-4 py-5 hover:text-accent">
              <span className="display text-3xl underline-offset-4 group-hover:underline">{l.label}</span>
              <span className="text-sm text-muted">{l.hint}</span>
            </Link>
          </li>
        ))}
      </ul>
      <div className="mt-8 max-w-3xl border-t border-fg">
        <Suspense fallback={null}>
          <ThisDaySection />
        </Suspense>
      </div>
    </>
  );
}
