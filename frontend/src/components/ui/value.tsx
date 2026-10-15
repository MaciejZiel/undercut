import type { ReactNode } from "react";
import { EM_DASH } from "@/lib/format";

/** Missing data: an em dash with a tooltip and a screen reader text. Never a zero. */
export function Dash({ label = "No data" }: { label?: string }) {
  return (
    <span title={label} className="text-muted">
      <span aria-hidden="true">{EM_DASH}</span>
      <span className="sr-only">{label}</span>
    </span>
  );
}

/** Render `value` when present, an em dash otherwise. Zero is a real value and is kept. */
export function orDash(value: ReactNode | null | undefined, label?: string): ReactNode {
  return value === null || value === undefined || value === "" ? <Dash label={label} /> : value;
}
