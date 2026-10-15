"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { UserIcon } from "@/components/ui/icons";
import { useAuth } from "@/lib/auth/auth-context";
import { initials } from "@/lib/format";

const ITEMS = [
  { href: "/", label: "My F1" },
  { href: "/predict/history", label: "My picks" },
  { href: "/leagues", label: "Leagues" },
  { href: "/settings", label: "Settings" },
] as const;

/** Header account control: a sign-in link for visitors, an avatar menu for members. */
export function AccountButton() {
  const auth = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const wrapper = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!wrapper.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  useEffect(() => {
    if (open) wrapper.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus();
  }, [open]);

  if (auth.status !== "authenticated" || !auth.user) {
    return (
      <Link
        href="/login"
        aria-label="Account: sign in"
        className="t-fast grid size-11 place-items-center border border-line-strong bg-bg text-fg hover:border-accent hover:text-accent"
      >
        <UserIcon />
      </Link>
    );
  }

  const name = auth.user.display_name ?? auth.user.email;

  function onKeyDown(e: React.KeyboardEvent) {
    const items = Array.from(wrapper.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? []);
    const i = items.indexOf(document.activeElement as HTMLElement);
    if (e.key === "Escape") {
      setOpen(false);
      trigger.current?.focus();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      items[(i + 1) % items.length]?.focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      items[(i - 1 + items.length) % items.length]?.focus();
    } else if (e.key === "Home") {
      e.preventDefault();
      items[0]?.focus();
    } else if (e.key === "End") {
      e.preventDefault();
      items[items.length - 1]?.focus();
    } else if (e.key === "Tab") {
      setOpen(false);
    }
  }

  const itemClass = "t-fast block w-full px-3 py-2.5 text-left text-sm hover:bg-surface focus:bg-surface";

  return (
    <div ref={wrapper} className="relative" onKeyDown={onKeyDown}>
      <button
        ref={trigger}
        type="button"
        aria-label={`Account menu for ${name}`}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => setOpen((v) => !v)}
        className="t-fast grid size-11 place-items-center bg-accent-soft text-sm font-extrabold text-accent"
      >
        {initials(name)}
      </button>
      {open && (
        <div
          id={menuId}
          role="menu"
          aria-label="Account"
          className="absolute right-0 top-12 z-40 w-56 border border-fg bg-bg p-1"
        >
          <p className="truncate px-3 py-2 text-sm text-muted">{name}</p>
          {ITEMS.map((item) => (
            <Link key={item.href + item.label} href={item.href} role="menuitem" onClick={() => setOpen(false)} className={itemClass}>
              {item.label}
            </Link>
          ))}
          <button
            type="button"
            role="menuitem"
            className={itemClass}
            onClick={async () => {
              setOpen(false);
              await auth.logout();
              router.push("/");
            }}
          >
            Log out
          </button>
        </div>
      )}
    </div>
  );
}
