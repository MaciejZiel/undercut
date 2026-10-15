"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { EmptyState } from "@/components/states/empty-state";
import { LoadingSkeleton } from "@/components/states/loading-skeleton";
import { ErrorState } from "@/components/states/error-state";
import { useAuth } from "@/lib/auth/auth-context";
import { loginHref } from "@/lib/auth/redirect";

/**
 * Gate for per-user screens. Anonymous visitors are sent to /login with the current
 * path (and query) kept in `next`, so they land back here after signing in. With `explain` they stay
 * on the page instead and read what they would get by signing in.
 */
export function RequireAuth({
  children,
  label = "Loading your account",
  explain,
}: {
  children: ReactNode;
  label?: string;
  explain?: { title: string; description: string };
}) {
  const auth = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (auth.status !== "anonymous" || explain) return;
    const target = `${window.location.pathname}${window.location.search}`;
    router.replace(loginHref(target));
  }, [auth.status, router, explain]);

  if (auth.status === "authenticated") return <>{children}</>;
  if (auth.status === "anonymous" && explain) {
    return (
      <div>
        <EmptyState title={explain.title} description={explain.description} />
        <div className="flex flex-wrap gap-4 text-sm font-bold">
          <Link href={loginHref(pathname)} className="text-accent underline underline-offset-4 hover:no-underline">
            Sign in
          </Link>
          <Link href="/register" className="text-accent underline underline-offset-4 hover:no-underline">
            Create an account
          </Link>
        </div>
      </div>
    );
  }
  if (auth.status === "error") {
    return <ErrorState title="Could not check your session" onRetry={() => void auth.refresh()} />;
  }
  return <LoadingSkeleton variant="text" rows={4} label={auth.status === "anonymous" ? "Redirecting to sign in" : label} />;
}
