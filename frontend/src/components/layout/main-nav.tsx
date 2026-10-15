"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS, isActive } from "@/lib/nav";
import { CatalogMenu } from "./catalog-menu";

function linkClass(active: boolean) {
  return [
    "t-fast relative inline-flex h-[4.5rem] items-center px-3.5 text-sm font-bold",
    active ? "text-accent" : "text-fg hover:text-accent",
    active ? "after:absolute after:inset-x-3.5 after:bottom-0 after:h-[3px] after:rounded-t-sm after:bg-accent" : "",
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
