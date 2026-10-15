import type { Metadata } from "next";
import { StandingsPage } from "@/components/standings/standings-view";

export const metadata: Metadata = {
  title: "Driver standings",
  description: "Championship table for any Formula 1 season and round, with a points progression chart.",
};

export default function DriverStandingsRoute({ searchParams }: PageProps<"/standings/drivers">) {
  return <StandingsPage kind="drivers" searchParams={searchParams} />;
}
