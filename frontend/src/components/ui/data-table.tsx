import Link from "next/link";
import type { ReactNode } from "react";
import { buildHref, nextOrdering, parseSort } from "@/lib/url";

/**
 * Accessible table shell: a visually hidden caption names it for screen
 * readers, and the wrapper scrolls horizontally so the page never does.
 */
export function DataTable({
  caption,
  children,
  minWidth = "34rem",
}: {
  caption: string;
  children: ReactNode;
  minWidth?: string;
}) {
  return (
    <div className="overflow-x-auto rounded-lg border border-line bg-surface">
      <table className="w-full border-collapse text-left text-sm" style={{ minWidth }}>
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  );
}

const headClass = "whitespace-nowrap border-b border-line bg-surface-2 px-3 py-2.5 text-xs font-bold uppercase tracking-wide text-muted";

export function Th({
  children,
  align = "left",
  className = "",
}: {
  children: ReactNode;
  align?: "left" | "right" | "center";
  className?: string;
}) {
  const a = align === "right" ? "text-right" : align === "center" ? "text-center" : "text-left";
  return (
    <th scope="col" className={`${headClass} ${a} ${className}`}>
      {children}
    </th>
  );
}

/** Column header that sorts through the URL (no client JS needed). */
export function SortTh({
  label,
  field,
  ordering,
  path,
  params,
  numeric = false,
  align = numeric ? "right" : "left",
}: {
  label: string;
  field: string;
  ordering: string;
  path: string;
  /** Current query, preserved when sorting. `page` is reset. */
  params: Record<string, string | number | undefined>;
  numeric?: boolean;
  align?: "left" | "right";
}) {
  const current = parseSort(ordering);
  const active = current.field === field;
  const ariaSort = active ? (current.desc ? "descending" : "ascending") : "none";
  const href = buildHref(path, { ...params, ordering: nextOrdering(ordering, field, numeric), page: undefined });
  return (
    <th
      scope="col"
      aria-sort={ariaSort}
      className={`${headClass} ${align === "right" ? "text-right" : "text-left"}`}
    >
      <Link
        href={href}
        scroll={false}
        className={`t-fast inline-flex items-center gap-1 hover:text-fg ${active ? "text-fg" : ""}`}
      >
        {label}
        <span aria-hidden="true" className="inline-block w-3 text-center">
          {active ? (current.desc ? "▼" : "▲") : ""}
        </span>
        <span className="sr-only">
          {active ? `, sorted ${ariaSort}. Activate to reverse.` : ", activate to sort"}
        </span>
      </Link>
    </th>
  );
}

export function Tr({ children, muted = false }: { children: ReactNode; muted?: boolean }) {
  return (
    <tr className={`border-b border-line last:border-b-0 hover:bg-surface-2/60 ${muted ? "text-muted" : ""}`}>
      {children}
    </tr>
  );
}

export function Td({
  children,
  align = "left",
  className = "",
}: {
  children: ReactNode;
  align?: "left" | "right" | "center";
  className?: string;
}) {
  const a = align === "right" ? "text-right" : align === "center" ? "text-center" : "text-left";
  return <td className={`px-3 py-2.5 align-middle ${a} ${className}`}>{children}</td>;
}

/** First cell of a row: the row header. */
export function RowTh({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <th scope="row" className={`px-3 py-2.5 text-left align-middle font-normal ${className}`}>
      {children}
    </th>
  );
}
