"use client";

import { useEffect, useState } from "react";
import { formatCountdown, remainingMs } from "@/lib/predict/api";

const TICK_MS = 1000;

/** Remaining time until `closesAt` on the server's clock (skew taken from the response's Date header). */
export function useRemaining(closesAt: string | null, skewMs: number): number | null {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!closesAt) return;
    const id = setInterval(() => setNow(Date.now()), TICK_MS);
    return () => clearInterval(id);
  }, [closesAt]);
  return remainingMs(closesAt, skewMs, now);
}

/** Ticking display. Calls onExpire once when it reaches zero so the page can ask the server again. */
export function Countdown({ closesAt, skewMs, onExpire }: { closesAt: string | null; skewMs: number; onExpire?: () => void }) {
  const remaining = useRemaining(closesAt, skewMs);
  const expired = remaining === 0;
  useEffect(() => {
    if (expired) onExpire?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expired]);
  if (remaining === null) return <span className="text-muted">Lock time not known yet</span>;
  if (expired) return <span className="font-bold">Predictions closed</span>;
  return (
    <span className="timing text-2xl font-extrabold" aria-label={`Predictions close in ${formatCountdown(remaining)}`}>
      {formatCountdown(remaining)}
    </span>
  );
}
