import { Suspense } from "react";
import { decodeKey } from "@/lib/auth/redirect";
import { ResetPasswordScreen } from "@/components/account/auth-forms";

export const metadata = { title: "Choose a new password" };

export default function ResetKeyPage({ params }: PageProps<"/reset/[key]">) {
  return (
    <Suspense fallback={null}>
      <Resolved params={params} />
    </Suspense>
  );
}

async function Resolved({ params }: { params: PageProps<"/reset/[key]">["params"] }) {
  const { key } = await params;
  return <ResetPasswordScreen resetKey={decodeKey(key)} />;
}
