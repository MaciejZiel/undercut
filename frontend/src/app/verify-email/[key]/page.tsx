import { Suspense } from "react";
import { VerifyEmailScreen } from "@/components/account/auth-forms";

export const metadata = { title: "Confirm your e-mail" };

export default function VerifyEmailPage({ params }: PageProps<"/verify-email/[key]">) {
  return (
    <Suspense fallback={null}>
      <Resolved params={params} />
    </Suspense>
  );
}

async function Resolved({ params }: { params: PageProps<"/verify-email/[key]">["params"] }) {
  const { key } = await params;
  return <VerifyEmailScreen verifyKey={key} />;
}
