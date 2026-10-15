"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS, isActive } from "@/lib/nav";
import { TAB_ICONS } from "@/components/ui/icons";

/** Bottom tab bar, visible below 768 px. Catalog opens a 4-tile screen. */
export function MobileTabBar() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Main (mobile)"
      data-testid="mobile-tab-bar"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface md:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
    >
      <ul className="grid grid-cols-5">
        {NAV_ITEMS.map((item) => {
          const active = isActive(item, pathname);
          const Icon = TAB_ICONS[item.icon];
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`t-fast relative flex h-[4.25rem] flex-col items-center justify-center gap-1 text-[0.6875rem] font-semibold ${
                  active ? "bg-accent-soft text-accent" : "text-muted"
                }`}
              >
                {active && (
                  <span
                    aria-hidden="true"
                    className="slant-bar absolute inset-x-4 top-0 h-[3px] bg-accent"
                  />
                )}
                <Icon />
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
