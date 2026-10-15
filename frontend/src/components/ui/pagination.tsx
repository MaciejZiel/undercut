import Link from "next/link";
import { buildHref } from "@/lib/url";

export function Pagination({
  path,
  params,
  page,
  pageSize,
  count,
}: {
  path: string;
  /** Current query without `page`. */
  params: Record<string, string | number | undefined>;
  page: number;
  pageSize: number;
  count: number;
}) {
  const pages = Math.max(1, Math.ceil(count / pageSize));
  if (count <= pageSize) return null;
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(count, page * pageSize);
  const href = (p: number) => buildHref(path, { ...params, page: p > 1 ? p : undefined });
  const btn = "t-fast rounded-md border border-line-strong bg-bg text-accent px-3 py-1.5 text-sm font-semibold hover:border-accent";
  const off = "rounded-sm border border-line px-3 py-1.5 text-sm font-semibold text-muted opacity-50";
  return (
    <nav aria-label="Pagination" className="mt-4 flex flex-wrap items-center justify-between gap-3">
      <p className="timing text-sm text-muted">
        {from}–{to} of {count}
      </p>
      <div className="flex items-center gap-2">
        {page > 1 ? (
          <Link href={href(page - 1)} rel="prev" className={btn}>
            Previous
          </Link>
        ) : (
          <span aria-disabled="true" className={off}>
            Previous
          </span>
        )}
        <span className="timing px-1 text-sm" aria-current="page">
          Page {page} of {pages}
        </span>
        {page < pages ? (
          <Link href={href(page + 1)} rel="next" className={btn}>
            Next
          </Link>
        ) : (
          <span aria-disabled="true" className={off}>
            Next
          </span>
        )}
      </div>
    </nav>
  );
}
