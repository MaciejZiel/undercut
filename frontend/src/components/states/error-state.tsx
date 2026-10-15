"use client";

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
    <section role="alert" className="border-l-4 border-danger py-1 pl-4">
      <h2 className="heading text-lg">{title}</h2>
      <p className="mt-1 max-w-xl text-muted">{description}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="t-fast mt-3 text-sm font-bold text-accent underline underline-offset-4 hover:no-underline"
        >
          Try again
        </button>
      )}
    </section>
  );
}
