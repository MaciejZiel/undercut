import Link from "next/link";
import { PageHeader } from "@/components/ui/page-header";
import { CATALOG_LINKS } from "@/lib/nav";

export const metadata = { title: "Catalog" };

export default function CatalogPage() {
  return (
    <>
      <PageHeader title="Catalog" description="Browse the sport by driver, team, track or year." />
      <ul className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {CATALOG_LINKS.map((l) => (
          <li key={l.href}>
            <Link
              href={l.href}
              className="t-fast flex h-full min-h-28 flex-col justify-end rounded-lg border border-line bg-surface p-4 hover:border-accent"
            >
              <span className="text-lg font-bold">{l.label}</span>
              <span className="text-sm text-muted">{l.hint}</span>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
