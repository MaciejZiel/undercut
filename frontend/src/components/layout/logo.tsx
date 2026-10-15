import Link from "next/link";

/** Wordmark: condensed capitals with a slanted yellow tick, the shape of a pit-lane marker. */
export function Logo() {
  return (
    <Link href="/" aria-label="Undercut, home" className="group flex items-baseline gap-2.5 rounded-sm py-1">
      <span aria-hidden="true" className="slant-bar inline-block h-2.5 w-[22px] translate-y-px bg-flag" />
      <span className="display text-[1.75rem] font-black leading-none tracking-[0.01em]">Undercut</span>
    </Link>
  );
}
