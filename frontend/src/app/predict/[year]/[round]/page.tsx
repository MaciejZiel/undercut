import { Suspense } from "react";
import { notFound } from "next/navigation";
import { PageHeader } from "@/components/ui/page-header";
import { LoadingSkeleton } from "@/components/states/loading-skeleton";
import { PredictNav } from "@/components/predict/predict-nav";
import { PredictRoundScreen } from "@/components/predict/round-screens";

export const metadata = { title: "Your pick" };

export default function PredictRoundPage({ params }: PageProps<"/predict/[year]/[round]">) {
  return (
    <Suspense fallback={<LoadingSkeleton variant="text" rows={4} />}>
      <Resolved params={params} />
    </Suspense>
  );
}

async function Resolved({ params }: { params: PageProps<"/predict/[year]/[round]">["params"] }) {
  const { year, round } = await params;
  const y = Number(year);
  const r = Number(round);
  if (!Number.isInteger(y) || !Number.isInteger(r) || y < 1950 || y > 2200 || r < 1 || r > 40) notFound();
  return (
    <>
      <PageHeader
        title="Your pick"
        description={`${y} round ${r}`}
        breadcrumbs={[{ label: "Predict", href: "/predict" }, { label: `${y} round ${r}` }]}
      />
      <PredictNav />
      <PredictRoundScreen year={y} round={r} />
    </>
  );
}
