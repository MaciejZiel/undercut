import { PageHeader } from "@/components/ui/page-header";
import { RequireAuth } from "@/components/account/require-auth";
import { SettingsScreen } from "@/components/account/settings-form";

export const metadata = { title: "Settings" };

export default function SettingsPage() {
  return (
    <>
      <PageHeader title="Settings" description="Your profile, preferences and data." />
      <RequireAuth>
        <SettingsScreen />
      </RequireAuth>
    </>
  );
}
