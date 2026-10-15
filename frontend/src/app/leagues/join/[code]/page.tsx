import { Suspense } from "react";
import { PageHeader } from "@/components/ui/page-header";
import { LoadingSkeleton } from "@/components/states/loading-skeleton";
import { JoinLeagueScreen } from "@/components/predict/leagues-screens";

export const metadata = { title: "Join a league" };

export default function JoinLeaguePage({ params }: PageProps<"/leagues/join/[code]">) {
  return (
    <Suspense fallback={<LoadingSkeleton variant="text" rows={3} />}>
      <Resolved params={params} />
    </Suspense>
  );
}

async function Resolved({ params }: { params: PageProps<"/leagues/join/[code]">["params"] }) {
  const { code } = await params;
  return (
    <>
      <PageHeader title="Join a league" />
      <JoinLeagueScreen code={code} />
    </>
  );
}
