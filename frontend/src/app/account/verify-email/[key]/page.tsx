import { redirect } from "next/navigation";
import { decodeKey } from "@/lib/auth/redirect";

export const metadata = { title: "Confirm your e-mail" };

/** The backend builds confirmation links as /account/verify-email/{key}. */
export default async function VerifyEmailAlias({ params }: PageProps<"/account/verify-email/[key]">) {
  const { key } = await params;
  redirect(`/verify-email/${encodeURIComponent(decodeKey(key))}`);
}
