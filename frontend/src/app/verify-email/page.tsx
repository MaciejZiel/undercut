import { PageHeader } from "@/components/ui/page-header";

export const metadata = { title: "Confirm your e-mail" };

/** Shown when someone opens /verify-email without the key from the mail. */
export default function VerifyEmailInfoPage() {
  return (
    <PageHeader
      title="Confirm your e-mail"
      description="Open the link in the message we sent you. Signed in already? Use the banner at the top of any page to send the link again."
    />
  );
}
