"use client";

import { useEffect, useRef } from "react";

/**
 * Put inside a `<details>` menu: it then closes on Escape and on a click anywhere else, which a bare
 * `<details>` does not do. Renders nothing visible.
 */
export function DetailsDismiss() {
  const marker = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const details = marker.current?.closest("details");
    if (!details) return;
    const onPointer = (e: PointerEvent) => {
      if (details.open && !details.contains(e.target as Node)) details.open = false;
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && details.open) {
        details.open = false;
        details.querySelector("summary")?.focus();
      }
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, []);
  return <span ref={marker} hidden />;
}
