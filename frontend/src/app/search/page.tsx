import { Suspense } from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/ui/page-header";
import { ListPageSkeleton } from "@/components/states/page-skeletons";
import { EmptyState } from "@/components/states/empty-state";
import { FilterForm } from "@/components/ui/filter-form";
import { searchCatalog } from "@/lib/api/queries";
import { MIN_QUERY_LENGTH, groupSuggestions } from "@/lib/search";
import { first } from "@/lib/url";

export const metadata: Metadata = {
  title: "Search",
  description: "Search drivers, constructors, circuits and races.",
};

export default function SearchPage({ searchParams }: PageProps<"/search">) {
  return (
    <>
      <PageHeader title="Search" breadcrumbs={[{ label: "Search" }]} />
      <Suspense fallback={<ListPageSkeleton filters rows={6} />}>
        <SearchResults searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function SearchResults({ searchParams }: { searchParams: PageProps<"/search">["searchParams"] }) {
  const q = first((await searchParams).q) ?? "";
  const form = (
    <FilterForm
      action="/search"
      resetHref="/search"
      active={false}
      fields={[{ kind: "text", name: "q", label: "Search drivers, teams, circuits and races", value: q, placeholder: "For example: raikkonen" }]}
    />
  );

  if (q.length < MIN_QUERY_LENGTH) {
    return (
      <>
        {form}
        <EmptyState
          title="Type at least 2 characters"
          description="Search ignores case and accents, so raikkonen finds Räikkönen."
        />
      </>
    );
  }

  const data = await searchCatalog(q);
  // The API already caps every group; show everything it returned.
  const groups = groupSuggestions(data, 100);

  return (
    <>
      {form}
      {groups.length === 0 ? (
        <EmptyState
          title={`No results for “${q}”`}
          description="Check the spelling or try a shorter name."
          action={{ label: "Browse drivers", href: "/drivers" }}
        />
      ) : (
        <div className="space-y-8">
          {groups.map((g) => (
            <section key={g.key} aria-labelledby={`g-${g.key}`}>
              <h2 id={`g-${g.key}`} className="mb-2 text-xl font-extrabold tracking-tight">
                {g.label}
              </h2>
              <ul className="divide-y divide-line rounded-lg border border-line bg-surface">
                {g.items.map((item) => (
                  <li key={item.id}>
                    <Link
                      href={item.href}
                      className="t-fast flex items-baseline justify-between gap-3 px-4 py-3 hover:bg-surface-2"
                    >
                      <span className="font-semibold">{item.label}</span>
                      {item.detail && <span className="text-sm text-muted">{item.detail}</span>}
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </>
  );
}
