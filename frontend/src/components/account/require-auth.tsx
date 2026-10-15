"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { LoadingSkeleton } from "@/components/states/loading-skeleton";
import { ErrorState } from "@/components/states/error-state";
import { useAuth } from "@/lib/auth/auth-context";
import { loginHref } from "@/lib/auth/redirect";

/**
 * Gate for per-user screens. Anonymous visitors are sent to /login with the current
 * path (and query) kept in `next`, so they land back here after signing in.
 */
export function RequireAuth({ children, label = "Loading your account" }: { children: ReactNode; label?: string }) {
  const auth = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (auth.status !== "anonymous") return;
    const target = `${window.location.pathname}${window.location.search}`;
    router.replace(loginHref(target));
  }, [auth.status, router]);

  if (auth.status === "authenticated") return <>{children}</>;
  if (auth.status === "error") {
    return <ErrorState title="Could not check your session" onRetry={() => void auth.refresh()} />;
  }
  return <LoadingSkeleton variant="text" rows={4} label={auth.status === "anonymous" ? "Redirecting to sign in" : label} />;
}
