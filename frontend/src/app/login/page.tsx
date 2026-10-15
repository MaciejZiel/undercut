import { Suspense } from "react";
import { LoginScreen } from "@/components/account/auth-forms";

export const metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginScreen />
    </Suspense>
  );
}
