"use client";

import { useEffect } from "react";
import { ErrorState } from "./error-state";

/** Shared body of the route-level error.tsx files. The header and footer keep working. */
export function RouteError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  return <ErrorState onRetry={retry} />;
}
