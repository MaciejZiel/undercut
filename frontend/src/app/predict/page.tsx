import { PageHeader } from "@/components/ui/page-header";
import { PredictNav } from "@/components/predict/predict-nav";
import { PredictHome } from "@/components/predict/round-screens";

export const metadata = { title: "Predict" };

export default function PredictPage() {
  return (
    <>
      <PageHeader title="Predict" description="Pick the podium, pole and fastest lap before qualifying starts and climb the leaderboard." />
      <PredictNav />
      <PredictHome />
    </>
  );
}
