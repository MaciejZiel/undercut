import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";
import { buildHref, nextOrdering, parseSort } from "@/lib/url";

/**
 * Accessible table shell: a visually hidden caption names it for screen
 * readers, and the wrapper scrolls horizontally so the page never does.
 */
export function DataTable({
  caption,
  children,
  minWidth = "34rem",
  stack = false,
}: {
  caption: string;
  children: ReactNode;
  minWidth?: string;
  /** Below 640 px the rows become two-line list items (the cells place themselves) and nothing scrolls sideways. */
  stack?: boolean;
}) {
  return (
    <div className="relative overflow-x-auto">
      <table
        className={`w-full border-collapse text-left text-sm ${stack ? "stack sm:min-w-[var(--table-min)]" : "min-w-[var(--table-min)]"}`}
        style={{ "--table-min": minWidth } as CSSProperties}
      >
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  );
}

const headClass = "eyebrow whitespace-nowrap border-b border-fg px-3 py-3";

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

export function Tr({ children, muted = false, className = "" }: { children: ReactNode; muted?: boolean; className?: string }) {
  return (
    <tr className={`border-b border-line hover:bg-surface/70 ${muted ? "text-muted" : ""} ${className}`}>
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
  return <td className={`px-3 py-3 align-middle ${a} ${className}`}>{children}</td>;
}

const HEX = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

/** First cell of a row: the row header. `color` draws the team colour as a bar on its left edge. */
export function RowTh({ children, className = "", color }: { children: ReactNode; className?: string; color?: string | null }) {
  const bar = color && HEX.test(color) ? color : null;
  return (
    <th
      scope="row"
      className={`px-3 py-3 text-left align-middle font-normal ${bar ? "border-l-[3px]" : ""} ${className}`}
      style={bar ? { borderLeftColor: bar } : undefined}
    >
      {children}
    </th>
  );
}
