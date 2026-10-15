import { Suspense } from "react";
import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/page-header";
import { LoadingSkeleton } from "@/components/states/loading-skeleton";
import { RaceSections, ThisDaySection, TopFiveSection } from "@/components/dashboard/sections";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "The next Formula 1 race, the latest podium and the championship top five.",
};

function HeroSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]" role="status" aria-busy="true">
      <span className="sr-only">Loading races…</span>
      <div className="skeleton h-56 rounded-lg" aria-hidden="true" />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3" aria-hidden="true">
        {Array.from({ length: 3 }, (_, i) => (
          <div key={i} className="skeleton h-40 rounded-lg" />
        ))}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <>
      <PageHeader title="Dashboard" description="Next race, latest podium and the championship top five." />
      <div className="flex flex-col gap-10">
        <Suspense fallback={<HeroSkeleton />}>
          <RaceSections />
        </Suspense>
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
          <Suspense fallback={<LoadingSkeleton variant="table" rows={5} label="Loading driver standings" />}>
            <TopFiveSection kind="drivers" />
          </Suspense>
          <Suspense fallback={<LoadingSkeleton variant="table" rows={5} label="Loading constructor standings" />}>
            <TopFiveSection kind="constructors" />
          </Suspense>
        </div>
        <Suspense fallback={<div className="skeleton h-24 rounded-lg" aria-hidden="true" />}>
          <ThisDaySection />
        </Suspense>
      </div>
    </>
  );
}
