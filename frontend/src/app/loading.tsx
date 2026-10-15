import { LoadingSkeleton } from "@/components/states/loading-skeleton";

export default function Loading() {
  return (
    <div>
      <div className="skeleton mb-3 h-9 w-64 max-w-full" />
      <div className="skeleton mb-8 h-4 w-96 max-w-full" />
      <LoadingSkeleton variant="table" />
    </div>
  );
}
