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
    <div className="mb-8">
      <Breadcrumbs items={breadcrumbs} />
      <h1 className="display text-4xl sm:text-5xl">{title}</h1>
      {description && <p className="mt-3 max-w-prose text-base text-muted sm:text-lg">{description}</p>}
      {children}
    </div>
  );
}
