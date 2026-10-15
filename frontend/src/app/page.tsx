import { Suspense } from "react";
import type { Metadata } from "next";
import { ChampionshipSection, LastRaceSection, Masthead, NextRaceSection } from "@/components/dashboard/sections";

export const metadata: Metadata = {
  title: "Weekend",
  description: "The next Formula 1 race weekend, the latest podium and the championship top five.",
};

function HeroSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,1fr)_23.5rem]" role="status" aria-busy="true">
      <span className="sr-only">Loading the race weekend…</span>
      <div className="skeleton h-96" aria-hidden="true" />
      <div className="skeleton h-96" aria-hidden="true" />
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

const stagger = (i: number) => ({ "--i": i }) as React.CSSProperties;

export default function DashboardPage() {
  return (
    <>
      <h1 className="sr-only">Undercut: next race weekend, latest podium and championship standings</h1>
      <Suspense fallback={<div className="h-8 border-b-4 border-fg" aria-hidden="true" />}>
        <Masthead />
      </Suspense>
      <Suspense fallback={<HeroSkeleton />}>
        <NextRaceSection />
      </Suspense>
      <div className="grid grid-cols-1 gap-x-12 gap-y-12 py-8 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <div className="rise" style={stagger(1)}>
          <Suspense fallback={<PanelSkeleton label="Loading the latest race" />}>
            <LastRaceSection />
          </Suspense>
        </div>
        <div className="rise" style={stagger(2)}>
          <Suspense fallback={<PanelSkeleton label="Loading the standings" />}>
            <ChampionshipSection />
          </Suspense>
        </div>
      </div>
    </>
  );
}
