import Link from "next/link";
import type { ReactNode } from "react";
import { circuitHref, constructorHref, driverHref, roundHref } from "@/lib/routes";
import { flagFor } from "@/lib/nationality";
import { Dash } from "./value";

const linkClass = "t-fast font-semibold hover:text-accent hover:underline underline-offset-2";

export function DriverLink({ slug, name }: { slug: string; name: string }) {
  return (
    <Link href={driverHref(slug)} className={linkClass}>
      {name}
    </Link>
  );
}

export function CircuitLink({ slug, name }: { slug: string; name: string }) {
  return (
    <Link href={circuitHref(slug)} className={linkClass}>
      {name}
    </Link>
  );
}

export function RoundLink({ year, round, name }: { year: number; round: number; name: string }) {
  return (
    <Link href={roundHref(year, round)} className={linkClass}>
      {name}
    </Link>
  );
}

const HEX = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

/** Team colour as a thin vertical bar, the one mark used for teams everywhere. Unknown colour gives a neutral bar. */
export function TeamBar({ color }: { color: string | null | undefined }) {
  const valid = color && HEX.test(color) ? color : null;
  return (
    <span
      aria-hidden="true"
      className="inline-block h-[1.1em] w-[3px] shrink-0 rounded-[1px] align-[-0.15em]"
      style={{ backgroundColor: valid ?? "var(--line-strong)" }}
    />
  );
}

export function ConstructorLink({
  slug,
  name,
  color,
  dot = true,
}: {
  slug: string;
  name: string;
  color?: string | null;
  /** Off where the row already shows the team colour. */
  dot?: boolean;
}) {
  return (
    <span className="inline-flex items-center gap-2">
      {dot && <TeamBar color={color} />}
      <Link href={constructorHref(slug)} className={linkClass}>
        {name}
      </Link>
    </span>
  );
}

/** Nationality or country with a flag emoji when known. */
export function Nationality({ value }: { value: string | null | undefined }) {
  if (!value) return <Dash />;
  const flag = flagFor(value);
  return (
    <span className="inline-flex items-center gap-1.5">
      {flag && (
        <span aria-hidden="true" className="text-base leading-none">
          {flag}
        </span>
      )}
      <span>{value}</span>
    </span>
  );
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "danger" | "accent" }) {
  const tones = {
    neutral: "bg-surface text-muted",
    danger: "bg-surface-2 text-danger",
    accent: "bg-flag text-on-flag",
  };
  return (
    <span className={`inline-block rounded-sm px-1.5 py-0.5 text-xs font-bold ${tones[tone]}`}>
      {children}
    </span>
  );
}
