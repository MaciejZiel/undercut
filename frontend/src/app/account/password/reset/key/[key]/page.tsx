import { redirect } from "next/navigation";

export const metadata = { title: "Choose a new password" };

/** The backend builds reset links as /account/password/reset/key/{key}. */
export default async function ResetKeyAlias({ params }: PageProps<"/account/password/reset/key/[key]">) {
  const { key } = await params;
  redirect(`/reset/${encodeURIComponent(key)}`);
}
