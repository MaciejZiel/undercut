import type { ReactNode } from "react";
import { Breadcrumbs, type Crumb } from "@/components/layout/breadcrumbs";

export function PageHeader({
  title,
  description,
  breadcrumbs = [],
  children,
}: {
  title: string;
  description?: string;
  breadcrumbs?: Crumb[];
  children?: ReactNode;
}) {
  return (
    <div className="mb-10">
      <Breadcrumbs items={breadcrumbs} />
      <h1 className="display text-5xl sm:text-6xl">{title}</h1>
      {description && <p className="mt-3 max-w-prose text-lg text-muted">{description}</p>}
      {children}
    </div>
  );
}
