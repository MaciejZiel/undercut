"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/predict", label: "Next race" },
  { href: "/predict/history", label: "My picks" },
  { href: "/predict/leaderboard", label: "Leaderboard" },
  { href: "/leagues", label: "Leagues" },
] as const;

export function PredictNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Predictions" className="mb-6 overflow-x-auto">
      <ul className="flex gap-1 border-b border-line">
        {TABS.map((t) => {
          const active = t.href === "/predict" ? pathname === "/predict" || /^\/predict\/\d/.test(pathname) : pathname === t.href || pathname.startsWith(`${t.href}/`);
          return (
            <li key={t.href}>
              <Link
                href={t.href}
                aria-current={active ? "page" : undefined}
                className={`t-fast block whitespace-nowrap border-b-2 px-3 py-2 text-sm font-semibold ${active ? "border-accent text-fg" : "border-transparent text-muted hover:text-fg"}`}
              >
                {t.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
