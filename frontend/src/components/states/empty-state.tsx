import Link from "next/link";
import type { ReactNode } from "react";
import { InboxIcon } from "@/components/ui/icons";

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
    <section className="flex flex-col items-center rounded-xl bg-surface px-6 py-12 text-center">
      <div className="mb-4 grid size-12 place-items-center rounded-full bg-bg text-accent">
        {icon ?? <InboxIcon />}
      </div>
      <h2 className="heading text-2xl">{title}</h2>
      {description && <p className="mt-1 max-w-md text-muted">{description}</p>}
      {action && (
        <Link
          href={action.href}
          className="t-fast mt-5 inline-flex min-h-11 items-center rounded-md bg-accent px-5 py-2 text-sm font-bold text-accent-fg hover:bg-accent-hover"
        >
          {action.label}
        </Link>
      )}
    </section>
  );
}
