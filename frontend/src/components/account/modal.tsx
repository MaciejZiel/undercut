"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Minimal accessible modal: role=dialog, labelled, Escape closes, Tab stays inside, focus returns
 * to the previously focused element. (A hand-rolled dialog keeps tests independent of
 * HTMLDialogElement support.)
 */
export function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  const titleId = useId();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const node = ref.current;
    const first = node?.querySelector<HTMLElement>(FOCUSABLE);
    (first ?? node)?.focus();
    return () => previous?.focus?.();
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-xl bg-bg p-5 shadow-xl outline-none"
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            e.stopPropagation();
            onClose();
            return;
          }
          if (e.key !== "Tab" || !ref.current) return;
          const items = Array.from(ref.current.querySelectorAll<HTMLElement>(FOCUSABLE));
          if (items.length === 0) return;
          const firstItem = items[0];
          const last = items[items.length - 1];
          if (e.shiftKey && document.activeElement === firstItem) {
            e.preventDefault();
            last.focus();
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            firstItem.focus();
          }
        }}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 id={titleId} className="heading text-xl sm:text-[1.375rem]">
            {title}
          </h2>
          <button type="button" onClick={onClose} aria-label="Close dialog" className="t-fast -mr-1 rounded-sm px-2 py-1 text-muted hover:bg-surface-2 hover:text-fg">
            <span aria-hidden="true">×</span>
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
