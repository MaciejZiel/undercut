"use client";

import { useEffect, type ReactNode } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { LoadingSkeleton } from "@/components/states/loading-skeleton";
import { isUnauthorized } from "@/lib/auth/api";
import { useAuth } from "@/lib/auth/auth-context";
import { describeError } from "@/lib/auth/messages";
import { isHttpError } from "@/lib/auth/http";

/**
 * Renders the five states of a data region: loading skeleton, error with retry, 401 (session
 * expired: re-reads /me, which makes <RequireAuth> redirect), 403 (message from the API, for
 * example the lock message) and empty.
 */
export function QueryState<T>({
  query,
  children,
  isEmpty,
  empty,
  skeleton,
  forbidden,
  errorTitle,
}: {
  query: UseQueryResult<T, unknown>;
  children: (data: T) => ReactNode;
  isEmpty?: (data: T) => boolean;
  empty?: { title: string; description?: string; action?: { label: string; href: string } };
  skeleton?: ReactNode;
  /** Title for 403 responses; the description is the API's message. */
  forbidden?: string;
  errorTitle?: string;
}) {
  const auth = useAuth();
  const unauthorized = query.isError && isUnauthorized(query.error);
  useEffect(() => {
    if (unauthorized) void auth.refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unauthorized]);

  if (query.isPending) return <>{skeleton ?? <LoadingSkeleton variant="table" rows={6} />}</>;
  if (query.isError) {
    if (unauthorized) return <LoadingSkeleton variant="text" rows={3} label="Session expired, redirecting" />;
    if (isHttpError(query.error) && query.error.status === 403) {
      return <EmptyState title={forbidden ?? "Not available"} description={describeError(query.error)} />;
    }
    return (
      <ErrorState
        title={errorTitle}
        description={isHttpError(query.error) ? describeError(query.error) : undefined}
        onRetry={() => void query.refetch()}
      />
    );
  }
  if (isEmpty?.(query.data) && empty) return <EmptyState {...empty} />;
  return <>{children(query.data)}</>;
}
