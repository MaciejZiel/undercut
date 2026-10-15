import Link from "next/link";

/** An original open inside-line mark, shared with the favicon and social card. */
export function Logo() {
  return (
    <Link href="/" aria-label="Undercut, home" className="flex shrink-0 items-center gap-2.5 rounded-sm py-1">
      <svg aria-hidden="true" width="28" height="30" viewBox="0 0 28 30" fill="none">
        <path d="M4 3v15a10 10 0 0 0 20 0V3" stroke="currentColor" strokeWidth="3" />
        <path d="M10 3v15a4 4 0 0 0 8 0v-7" stroke="currentColor" strokeWidth="3" />
      </svg>
      <span className="display text-[2rem] font-bold leading-none tracking-tight">undercut</span>
    </Link>
  );
}
