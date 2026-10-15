import { PageHeader } from "@/components/ui/page-header";
import { HistoryScreen } from "@/components/predict/history-screen";
import { PredictNav } from "@/components/predict/predict-nav";

export const metadata = { title: "My picks" };

export default function PredictHistoryPage() {
  return (
    <>
      <PageHeader title="My picks" description="Every prediction you made, with the real result and your points." />
      <PredictNav />
      <HistoryScreen />
    </>
  );
}
