import Link from "next/link";

export function Logo() {
  return (
    <Link
      href="/"
      aria-label="Undercut, home"
      className="group flex items-center gap-2 rounded-md py-1 font-extrabold tracking-tight"
    >
      <svg viewBox="0 0 28 28" width="26" height="26" aria-hidden="true" focusable="false">
        <path d="M3 4h7l5 14 5-14h5L18 24h-6L3 4z" fill="var(--fg)" />
        <path d="M2 20 26 10v4L2 24z" fill="var(--accent)" />
      </svg>
      <span className="text-xl leading-none">Undercut</span>
    </Link>
  );
}
