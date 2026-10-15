import { SPEEDS, type Speed } from "./format";

export type ReplayUrlState = { t: number; speed: Speed };

/** Parse ?t= (seconds) and ?speed= from a query string; invalid values fall back to 0 and 1x. */
export function parseReplayParams(search: string, duration: number): ReplayUrlState {
  const p = new URLSearchParams(search);
  const rawT = p.get("t");
  const t = rawT !== null && /^\d+(\.\d+)?$/.test(rawT) ? Number(rawT) : 0;
  const rawSpeed = Number(p.get("speed"));
  const speed = (SPEEDS as readonly number[]).includes(rawSpeed) ? (rawSpeed as Speed) : 1;
  return { t: Math.min(Math.max(0, t), Math.max(0, duration)), speed };
}

/** Same query string with t (whole seconds) and speed set; speed 1 and t 0 are left out. */
export function withReplayParams(search: string, state: ReplayUrlState): string {
  const p = new URLSearchParams(search);
  const t = Math.max(0, Math.floor(state.t));
  if (t > 0) p.set("t", String(t));
  else p.delete("t");
  if (state.speed !== 1) p.set("speed", String(state.speed));
  else p.delete("speed");
  const s = p.toString();
  return s ? `?${s}` : "";
}
