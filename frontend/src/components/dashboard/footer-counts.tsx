"use client";

import { useEffect, useState } from "react";
import { createApiClient, type components } from "@/lib/api/client";
import { formatInteger } from "@/lib/format";

type Counts = components["schemas"]["Counts"];

// One request per page load, shared by every footer instance (the footer stays mounted anyway).
let pending: Promise<Counts | null> | null = null;

function loadCounts(): Promise<Counts | null> {
  pending ??= createApiClient(window.location.origin)
    .GET("/api/v1/dashboard/")
    .then(({ data }) => data?.counts ?? null)
    .catch(() => null)
    .then((counts) => {
      if (counts === null) pending = null; // allow a retry on the next mount
      return counts;
    });
  return pending;
}

/** Reset for tests. */
export function resetFooterCounts() {
  pending = null;
}

/** "{N} seasons · {N} races · {N} drivers"; renders nothing while loading or when the API fails. */
export function FooterCounts() {
  const [counts, setCounts] = useState<Counts | null>(null);
  useEffect(() => {
    let alive = true;
    void loadCounts().then((c) => alive && setCounts(c));
    return () => {
      alive = false;
    };
  }, []);
  const seasons = formatInteger(counts?.seasons);
  const races = formatInteger(counts?.races);
  const drivers = formatInteger(counts?.drivers);
  if (seasons === null || races === null || drivers === null) return null;
  return (
    <p className="mx-auto max-w-7xl px-5 pb-6 md:px-8 text-sm text-muted">
      {seasons} seasons · {races} races · {drivers} drivers
    </p>
  );
}
