export type CountdownParts = { days: number; hours: number; minutes: number; seconds: number };

/** Split a remaining time into parts; null once the moment has passed. */
export function countdownParts(targetMs: number, nowMs: number): CountdownParts | null {
  const diff = Math.floor((targetMs - nowMs) / 1000);
  if (!Number.isFinite(diff) || diff <= 0) return null;
  return {
    days: Math.floor(diff / 86400),
    hours: Math.floor((diff % 86400) / 3600),
    minutes: Math.floor((diff % 3600) / 60),
    seconds: diff % 60,
  };
}
