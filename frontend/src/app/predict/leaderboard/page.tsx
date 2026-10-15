import { PageHeader } from "@/components/ui/page-header";
import { LeaderboardPanel } from "@/components/predict/leaderboard";
import { PredictNav } from "@/components/predict/predict-nav";

export const metadata = { title: "Prediction leaderboard" };

export default function LeaderboardPage() {
  return (
    <>
      <PageHeader title="Leaderboard" description="The best predictors, by season or by round." />
      <PredictNav />
      <LeaderboardPanel />
    </>
  );
}
