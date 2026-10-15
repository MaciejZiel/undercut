import { PageHeader } from "@/components/ui/page-header";
import { LeaguesScreen } from "@/components/predict/leagues-screens";
import { PredictNav } from "@/components/predict/predict-nav";

export const metadata = { title: "Leagues" };

export default function LeaguesPage() {
  return (
    <>
      <PageHeader title="Leagues" description="Compete with friends in a private leaderboard." />
      <PredictNav />
      <LeaguesScreen />
    </>
  );
}
