"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS, isActive } from "@/lib/nav";
import { CatalogMenu } from "./catalog-menu";

function linkClass(active: boolean) {
  return [
    "t-fast relative inline-flex h-16 items-center px-3 text-[0.9375rem] font-semibold",
    active ? "text-fg" : "text-muted hover:text-fg",
    active
      ? "after:slant-bar after:absolute after:inset-x-3 after:bottom-0 after:h-[4px] after:bg-flag"
      : "",
  ].join(" ");
}

/** Desktop navigation (hidden below 768 px, where the tab bar takes over). */
export function MainNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className="hidden md:block">
      <ul className="flex items-center">
        {NAV_ITEMS.map((item) =>
          item.label === "Catalog" ? (
            <CatalogMenu key={item.href} linkClass={linkClass} />
          ) : (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={isActive(item, pathname) ? "page" : undefined}
                className={linkClass(isActive(item, pathname))}
              >
                {item.label}
              </Link>
            </li>
          ),
        )}
      </ul>
    </nav>
  );
}
