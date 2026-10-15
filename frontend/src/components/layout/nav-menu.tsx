"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { isActive, type NavItem } from "@/lib/nav";
import { ChevronDownIcon } from "@/components/ui/icons";

/** Disclosure-style dropdown: a button toggles the links of a navigation group. */
export function NavMenu({ item, linkClass }: { item: NavItem; linkClass: (active: boolean) => string }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLLIElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  const pathname = usePathname();
  const active = isActive(item, pathname);

  useEffect(() => {
    // Close after navigating: reacts to an external change (the route).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!open) return;
    const onPointer = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointer);
    return () => document.removeEventListener("pointerdown", onPointer);
  }, [open]);

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape" && open) {
      setOpen(false);
      buttonRef.current?.focus();
    } else if (e.key === "ArrowDown" && !open && e.target === buttonRef.current) {
      e.preventDefault();
      setOpen(true);
    }
  }

  // Close when focus leaves the whole widget (Tab out).
  function onBlur(e: React.FocusEvent) {
    if (!rootRef.current?.contains(e.relatedTarget as Node | null)) setOpen(false);
  }

  return (
    <li ref={rootRef} className="relative" onKeyDown={onKeyDown} onBlur={onBlur}>
      <button
        ref={buttonRef}
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        aria-current={active ? "true" : undefined}
        onClick={() => setOpen((o) => !o)}
        className={`${linkClass(active)} gap-1`}
      >
        {item.label}
        <ChevronDownIcon className={open ? "rotate-180" : ""} />
      </button>
      <ul
        id={panelId}
        hidden={!open}
        className="absolute left-0 top-full z-30 -mt-1 w-64 border border-fg bg-bg p-1.5"
      >
        {item.children?.map((l) => (
          <li key={l.href}>
            <Link
              href={l.href}
              className="t-fast flex flex-col px-3 py-2.5 hover:bg-surface"
            >
              <span className="font-semibold">{l.label}</span>
              <span className="text-xs text-muted">{l.hint}</span>
            </Link>
          </li>
        ))}
      </ul>
    </li>
  );
}
