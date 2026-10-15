"use client";

import { useEffect, useRef } from "react";

/**
 * Makes a GET filter form apply as soon as a list is changed, so nobody has to find the Apply button.
 * Changing the season clears "after round", whose choices belong to the season that was shown. Without
 * JavaScript the form still works with its button.
 */
export function FilterAutoSubmit() {
  const marker = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const form = marker.current?.closest("form");
    if (!form) return;
    const onChange = (event: Event) => {
      const target = event.target;
      if (!(target instanceof HTMLSelectElement)) return;
      if (target.name === "season") {
        const round = form.elements.namedItem("after_round");
        if (round instanceof HTMLSelectElement) round.value = "";
      }
      form.requestSubmit();
    };
    form.addEventListener("change", onChange);
    return () => form.removeEventListener("change", onChange);
  }, []);
  return <span ref={marker} hidden />;
}
