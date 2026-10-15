"use client";

import { useLayoutEffect, useRef, type RefObject } from "react";

export const FLIP_MS = 180;
/** Larger jumps (seek, lap jump) are not animated: 20 rows flying around is noise. */
const MAX_ANIMATED_FRAME_JUMP = 2;

/** Put each moved row back where it was, without a transition. Returns the rows that moved. */
function offsetMovedRows(body: HTMLTableSectionElement, oldOrder: string[], rowHeight: number): HTMLElement[] {
  const oldIndex = new Map(oldOrder.map((id, i) => [id, i]));
  const moved: HTMLElement[] = [];
  for (let i = 0; i < body.rows.length; i++) {
    const row = body.rows[i];
    const from = oldIndex.get(row.dataset.id ?? "");
    if (from === undefined || from === i) continue;
    row.style.transition = "none";
    row.style.transform = `translateY(${(from - i) * rowHeight}px)`;
    moved.push(row);
  }
  return moved;
}

/** Let the offset rows slide to their new place. */
function releaseRows(rows: HTMLElement[]) {
  for (const row of rows) {
    row.style.transition = `transform ${FLIP_MS}ms ease-out`;
    row.style.transform = "";
  }
}

/**
 * FLIP reordering for table rows. The DOM order always follows the race order (so the table
 * reads correctly for assistive technology); when rows move, each moved row is first offset to
 * where it was (transform only, no layout) and then transitions to its new place. One layout
 * read per reorder (the row height), none per frame. Disabled under prefers-reduced-motion.
 */
export function useFlip(tbody: RefObject<HTMLTableSectionElement | null>, order: string, frameIndex: number) {
  const previous = useRef<{ order: string[]; frame: number } | null>(null);

  useLayoutEffect(() => {
    const body = tbody.current;
    if (!body) return;
    const ids = order ? order.split(",") : [];
    const before = previous.current;
    previous.current = { order: ids, frame: frameIndex };
    if (!before || before.order.join(",") === order) return;
    if (Math.abs(frameIndex - before.frame) > MAX_ANIMATED_FRAME_JUMP) return;
    if (typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const rowHeight = body.rows[0]?.offsetHeight ?? 0;
    if (!rowHeight) return;

    const moved = offsetMovedRows(body, before.order, rowHeight);
    if (moved.length === 0) return;
    const raf = window.requestAnimationFrame(() => {
      releaseRows(moved);
    });
    return () => window.cancelAnimationFrame(raf);
  }, [tbody, order, frameIndex]);
}
