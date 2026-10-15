import { Suspense } from "react";
import { PageHeader } from "@/components/ui/page-header";
import { LoadingSkeleton } from "@/components/states/loading-skeleton";
import { LeagueScreen } from "@/components/predict/leagues-screens";
import { PredictNav } from "@/components/predict/predict-nav";

export const metadata = { title: "League" };

export default function LeaguePage({ params }: PageProps<"/leagues/[code]">) {
  return (
    <Suspense fallback={<LoadingSkeleton variant="text" rows={4} />}>
      <Resolved params={params} />
    </Suspense>
  );
}

async function Resolved({ params }: { params: PageProps<"/leagues/[code]">["params"] }) {
  const { code } = await params;
  return (
    <>
      <PageHeader title="League" breadcrumbs={[{ label: "Leagues", href: "/leagues" }, { label: "League" }]} />
      <PredictNav />
      <LeagueScreen code={code} />
    </>
  );
}
