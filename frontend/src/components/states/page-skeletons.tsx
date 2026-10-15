import { LoadingSkeleton } from "./loading-skeleton";

/** Fixed heights so content swaps in without layout shift. */
export function ListPageSkeleton({ rows = 10, filters = true }: { rows?: number; filters?: boolean }) {
  return (
    <div>
      <div className="mb-8">
        <div className="skeleton mb-3 h-9 w-56 max-w-full" />
        <div className="skeleton h-4 w-80 max-w-full" />
      </div>
      {filters && <div className="skeleton mb-5 h-[4.25rem] w-full rounded-sm" aria-hidden="true" />}
      <LoadingSkeleton variant="table" rows={rows} />
    </div>
  );
}

export function DetailPageSkeleton() {
  return (
    <div>
      <div className="mb-8 flex items-center gap-4" aria-hidden="true">
        <div className="skeleton size-16 rounded-sm" />
        <div>
          <div className="skeleton mb-2 h-9 w-64 max-w-full" />
          <div className="skeleton h-4 w-40" />
        </div>
      </div>
      <div className="mb-8 grid grid-cols-2 gap-3 lg:grid-cols-4" aria-hidden="true">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="skeleton h-[5.25rem] rounded-sm" />
        ))}
      </div>
      <LoadingSkeleton variant="table" rows={6} />
    </div>
  );
}
