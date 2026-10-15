import { Suspense } from "react";
import type { Metadata } from "next";
import { LoadingSkeleton } from "@/components/states/loading-skeleton";
import { RaceSections, ThisDaySection, TopFiveSection } from "@/components/dashboard/sections";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "The next Formula 1 race, the latest podium and the championship top five.",
};

function HeroSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]" role="status" aria-busy="true">
      <span className="sr-only">Loading races…</span>
      <div className="skeleton h-72" aria-hidden="true" />
      <div className="skeleton h-72" aria-hidden="true" />
    </div>
  );
}

export default function DashboardPage() {
  return (
    <>
      <h1 className="sr-only">Undercut dashboard: next race, latest podium and championship standings</h1>
      <div className="flex flex-col gap-14">
        <Suspense fallback={<HeroSkeleton />}>
          <RaceSections />
        </Suspense>
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-2 lg:gap-16">
          <Suspense fallback={<LoadingSkeleton variant="table" rows={5} label="Loading driver standings" />}>
            <TopFiveSection kind="drivers" />
          </Suspense>
          <Suspense fallback={<LoadingSkeleton variant="table" rows={5} label="Loading constructor standings" />}>
            <TopFiveSection kind="constructors" />
          </Suspense>
        </div>
        <Suspense fallback={<div className="skeleton h-24" aria-hidden="true" />}>
          <ThisDaySection />
        </Suspense>
      </div>
    </>
  );
}
