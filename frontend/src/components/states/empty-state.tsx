import Link from "next/link";
import type { ReactNode } from "react";

/** Icon, one sentence, one action. */
export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string;
  description?: string;
  action?: { label: string; href: string };
  icon?: ReactNode;
}) {
  return (
    <section className="border-t border-line py-6">
      {icon && <div className="mb-3 text-muted">{icon}</div>}
      <h2 className="heading text-lg">{title}</h2>
      {description && <p className="mt-1 max-w-xl text-muted">{description}</p>}
      {action && (
        <Link
          href={action.href}
          className="t-fast mt-3 inline-block text-sm font-bold text-accent underline underline-offset-4 hover:no-underline"
        >
          {action.label}
        </Link>
      )}
    </section>
  );
}
