import Link from "next/link";

/** Wordmark: the name in black capitals and a red arrow, the line that gets past a car. */
export function Logo({ className = "" }: { className?: string }) {
  return (
    <Link href="/" aria-label="Undercut, home" className={`group inline-flex items-baseline gap-0.5 py-1 ${className}`}>
      <span className="display text-[1.5rem] leading-none">undercut</span>
      <svg viewBox="0 0 24 24" aria-hidden="true" className="size-5 translate-y-0.5 self-center fill-none stroke-accent" strokeWidth={3.2} strokeLinecap="square">
        <path d="M6 18 18 6M8 6h10v10" />
      </svg>
    </Link>
  );
}
