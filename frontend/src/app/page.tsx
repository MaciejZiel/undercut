import { Suspense } from "react";
import type { Metadata } from "next";
import {
  ArchiveSection,
  ChampionshipSection,
  LastRaceSection,
  NextRaceSection,
  PredictionInvite,
  ThisDaySection,
} from "@/components/dashboard/sections";

export const metadata: Metadata = {
  title: "This weekend",
  description: "The next Formula 1 race weekend, the latest podium and the championship top five.",
};

function HeroSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,1.88fr)_minmax(20rem,1fr)]" role="status" aria-busy="true">
      <span className="sr-only">Loading the race weekend…</span>
      <div className="skeleton h-96" aria-hidden="true" />
      <div className="skeleton h-96 rounded-xl" aria-hidden="true" />
    </div>
  );
}

function PanelSkeleton({ label }: { label: string }) {
  return (
    <div role="status" aria-busy="true" className="skeleton h-80">
      <span className="sr-only">{label}</span>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <>
      <h1 className="sr-only">Undercut: next race weekend, latest podium and championship standings</h1>
      <div className="flex flex-col gap-16">
        <Suspense fallback={<HeroSkeleton />}>
          <NextRaceSection />
        </Suspense>
        <div className="grid grid-cols-1 gap-14 border-t border-line pt-14 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] lg:gap-20">
          <Suspense fallback={<PanelSkeleton label="Loading the latest race" />}>
            <LastRaceSection />
          </Suspense>
          <Suspense fallback={<PanelSkeleton label="Loading the standings" />}>
            <ChampionshipSection />
          </Suspense>
        </div>
        <Suspense fallback={<div className="skeleton h-28 rounded-xl" aria-hidden="true" />}>
          <PredictionInvite />
        </Suspense>
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] lg:gap-20">
          <Suspense fallback={<div className="skeleton h-40" aria-hidden="true" />}>
            <ArchiveSection />
          </Suspense>
          <Suspense fallback={<div className="skeleton h-40 rounded-xl" aria-hidden="true" />}>
            <ThisDaySection />
          </Suspense>
        </div>
      </div>
    </>
  );
}
