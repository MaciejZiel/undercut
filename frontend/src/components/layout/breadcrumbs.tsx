import Link from "next/link";

export type Crumb = { label: string; href?: string };

/**
 * Detail pages pass their trail; the last item is the current page.
 * Desktop shows the full trail, mobile only a back link to the parent.
 */
export function Breadcrumbs({ items }: { items: Crumb[] }) {
  if (items.length === 0) return null;
  const parent = [...items].reverse().find((c) => c.href);
  return (
    <>
      <nav aria-label="Breadcrumb" className="mb-3 hidden text-sm text-muted md:block">
        <ol className="flex flex-wrap items-center gap-x-2">
          {items.map((c, i) => (
            <li key={`${c.label}-${i}`} className="flex items-center gap-2">
              {c.href && i < items.length - 1 ? (
                <Link href={c.href} className="hover:text-fg hover:underline">
                  {c.label}
                </Link>
              ) : (
                <span aria-current="page" className="text-fg">
                  {c.label}
                </span>
              )}
              {i < items.length - 1 && <span aria-hidden="true">/</span>}
            </li>
          ))}
        </ol>
      </nav>
      {parent && (
        <Link href={parent.href!} className="mb-3 inline-block text-sm text-muted hover:text-fg md:hidden">
          <span aria-hidden="true">&larr; </span>
          Back to {parent.label}
        </Link>
      )}
    </>
  );
}
