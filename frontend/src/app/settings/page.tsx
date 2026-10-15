import { Suspense } from "react";
import { PageHeader } from "@/components/ui/page-header";
import { RequireAuth } from "@/components/account/require-auth";
import { SettingsScreen } from "@/components/account/settings-form";

export const metadata = { title: "Settings" };

export default function SettingsPage() {
  return (
    <>
      <PageHeader title="Settings" description="Your profile, preferences and data." />
      <RequireAuth>
        <Suspense fallback={null}>
          <SettingsScreen />
        </Suspense>
      </RequireAuth>
    </>
  );
}
