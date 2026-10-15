"use client";

import { AlertIcon } from "@/components/ui/icons";

/** Network or 5xx failure. Scoped to a region so the rest of the page keeps working. */
export function ErrorState({
  title = "Could not load the data",
  description = "Something went wrong on our side. Your connection may be fine.",
  onRetry,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  return (
    <section
      role="alert"
      className="flex flex-col items-center rounded-xl bg-surface px-6 py-12 text-center"
    >
      <div className="mb-4 grid size-12 place-items-center rounded-full bg-bg text-danger">
        <AlertIcon />
      </div>
      <h2 className="heading text-2xl">{title}</h2>
      <p className="mt-1 max-w-md text-muted">{description}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="t-fast mt-5 inline-flex min-h-11 items-center rounded-md bg-accent px-5 py-2 text-sm font-bold text-accent-fg hover:bg-accent-hover"
        >
          Try again
        </button>
      )}
    </section>
  );
}
