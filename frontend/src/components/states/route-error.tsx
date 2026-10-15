"use client";

import { useEffect } from "react";
import { ErrorState } from "./error-state";

/** Shared body of the route-level error.tsx files. The header and footer keep working. */
export function RouteError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <>
      {/* The failed page had its own h1; keep one so the heading order stays valid. */}
      <h1 className="sr-only">Something went wrong</h1>
      <ErrorState onRetry={retry} />
    </>
  );
}
