"use client";

import { useEffect } from "react";
import { ErrorState } from "@/components/states/error-state";

export default function RouteError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  return <ErrorState onRetry={retry} />;
}
