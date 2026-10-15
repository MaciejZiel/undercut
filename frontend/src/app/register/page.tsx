import { Suspense } from "react";
import { RegisterScreen } from "@/components/account/auth-forms";

export const metadata = { title: "Create an account" };

export default function RegisterPage() {
  return (
    <Suspense fallback={null}>
      <RegisterScreen />
    </Suspense>
  );
}
