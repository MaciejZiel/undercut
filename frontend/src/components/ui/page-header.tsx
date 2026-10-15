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
      <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{title}</h1>
      {description && <p className="mt-2 max-w-prose text-muted">{description}</p>}
      {children}
    </div>
  );
}
