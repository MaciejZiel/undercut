import { LoadingSkeleton } from "@/components/states/loading-skeleton";

export default function Loading() {
  return <LoadingSkeleton variant="cards" rows={6} label="Loading the calendar" />;
}
