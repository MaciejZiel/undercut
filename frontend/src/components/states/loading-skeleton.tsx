type Variant = "table" | "cards" | "text";

/**
 * Skeleton in the shape of the final content (never a full-page spinner).
 * Deliberately static: no looping animation.
 */
export function LoadingSkeleton({
  variant = "table",
  rows = 8,
  label = "Loading",
}: {
  variant?: Variant;
  rows?: number;
  label?: string;
}) {
  return (
    <div role="status" aria-live="polite" aria-busy="true" data-variant={variant}>
      <span className="sr-only">{label}…</span>
      {variant === "table" && (
        <div className="overflow-hidden rounded-sm border border-line bg-surface" aria-hidden="true">
          <div className="flex gap-4 border-b border-line px-4 py-3">
            <div className="skeleton h-3 w-8" />
            <div className="skeleton h-3 w-32" />
            <div className="skeleton ml-auto h-3 w-12" />
          </div>
          {Array.from({ length: rows }, (_, i) => (
            <div key={i} className="flex items-center gap-4 border-b border-line px-4 py-3 last:border-b-0">
              <div className="skeleton h-4 w-8" />
              <div className="skeleton h-4 w-40 max-w-[50%]" />
              <div className="skeleton ml-auto h-4 w-14" />
            </div>
          ))}
        </div>
      )}
      {variant === "cards" && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-hidden="true">
          {Array.from({ length: rows > 6 ? 6 : rows }, (_, i) => (
            <div key={i} className="rounded-sm border border-line bg-surface p-4">
              <div className="skeleton mb-4 h-3 w-1/3" />
              <div className="skeleton mb-2 h-6 w-2/3" />
              <div className="skeleton h-3 w-full" />
            </div>
          ))}
        </div>
      )}
      {variant === "text" && (
        <div className="space-y-3" aria-hidden="true">
          {Array.from({ length: rows }, (_, i) => (
            <div key={i} className="skeleton h-4" style={{ width: `${95 - (i % 3) * 18}%` }} />
          ))}
        </div>
      )}
    </div>
  );
}
