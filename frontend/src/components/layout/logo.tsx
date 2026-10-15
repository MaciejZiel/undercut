import Link from "next/link";

/** Wordmark: a "U" cut by a diagonal (the undercut) and the name in lower case. */
export function Logo() {
  return (
    <Link href="/" aria-label="Undercut, home" className="flex items-center gap-2 rounded-md py-1 text-accent">
      <svg viewBox="0 0 38 38" aria-hidden="true" className="size-8 fill-none stroke-current" strokeWidth={3} strokeLinecap="square">
        <path d="M5 6v15a12 12 0 0 0 24 0V6M13 6v15a4 4 0 0 0 8 0V6" />
        <path d="m3 30 30-17" style={{ stroke: "var(--bg)" }} strokeWidth={5} />
      </svg>
      <span className="text-[1.625rem] font-extrabold leading-none tracking-[-0.06em]">undercut</span>
    </Link>
  );
}
