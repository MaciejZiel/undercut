import type { ReactNode } from "react";
import { Breadcrumbs, type Crumb } from "@/components/layout/breadcrumbs";
import { initials } from "@/lib/format";

const HEX = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

/**
 * Detail page header: initials on a neutral accent instead of a photo, with the
 * team colour as a thin bar on the left (an accent, never a background).
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
    <div className="mb-8">
      <Breadcrumbs items={breadcrumbs} />
      <div className="flex items-center gap-4">
        <span
          aria-hidden="true"
          className="h-16 w-1.5 shrink-0 rounded-full border border-line"
          style={{ backgroundColor: bar ?? "var(--line)" }}
        />
        <span
          aria-hidden="true"
          className="grid size-16 shrink-0 place-items-center rounded-lg bg-accent-soft text-2xl font-extrabold tracking-tight text-accent"
        >
          {initials(title)}
        </span>
        <div className="min-w-0">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{title}</h1>
          {subtitle && <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-muted">{subtitle}</div>}
        </div>
      </div>
      {children}
    </div>
  );
}
