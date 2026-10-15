import type { Metadata } from "next";
import { StandingsPage } from "@/components/standings/standings-view";

export const metadata: Metadata = {
  title: "Constructor standings",
  description: "Championship table for any Formula 1 season and round, with a points progression chart.",
};

export default function ConstructorStandingsRoute({ searchParams }: PageProps<"/standings/constructors">) {
  return <StandingsPage kind="constructors" searchParams={searchParams} />;
}
