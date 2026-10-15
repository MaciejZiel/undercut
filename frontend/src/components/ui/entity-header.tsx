import type { ReactNode } from "react";
import { Breadcrumbs, type Crumb } from "@/components/layout/breadcrumbs";

const HEX = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

/**
 * Detail page header: the name set large and condensed, the team colour as a bar beside it, and
 * the page's actions (follow, compare) in one row underneath.
 */
export function EntityHeader({
  title,
  subtitle,
  breadcrumbs,
  accentColor,
  children,
}: {
  title: string;
  subtitle?: ReactNode;
  breadcrumbs: Crumb[];
  accentColor?: string | null;
  children?: ReactNode;
}) {
  const bar = accentColor && HEX.test(accentColor) ? accentColor : null;
  return (
    <div className="mb-10 border-b border-line pb-8">
      <Breadcrumbs items={breadcrumbs} />
      <div className="flex items-stretch gap-5">
        <span aria-hidden="true" className="w-2 shrink-0 rounded-[1px]" style={{ backgroundColor: bar ?? "var(--line)" }} />
        <div className="min-w-0">
          <h1 className="display text-5xl sm:text-7xl">{title}</h1>
          {subtitle && <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-muted">{subtitle}</div>}
        </div>
      </div>
      {children && <div className="mt-6 flex flex-wrap items-center gap-3">{children}</div>}
    </div>
  );
}
