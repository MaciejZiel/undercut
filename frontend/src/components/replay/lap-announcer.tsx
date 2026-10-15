"use client";

import { useEffect, useRef, useState } from "react";
import { lapAtTime } from "@/lib/replay/frame";
import type { PlaybackController } from "@/lib/replay/controller";
import { usePlayback } from "./use-playback";

/** At most one announcement per interval while playing; immediate when paused or after a seek. */
export const ANNOUNCE_INTERVAL_MS = 5000;

/** Visually hidden polite live region: announces lap changes, never every frame. */
export function LapAnnouncer({
  controller,
  laps,
  totalLaps,
}: {
  controller: PlaybackController;
  laps: { lap: number; t: number }[];
  totalLaps: number | null;
}) {
  const lap = usePlayback(controller, (s) => lapAtTime(laps, s.t) ?? 0);
  const playing = usePlayback(controller, (s) => s.playing);
  const [text, setText] = useState("");
  const last = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!lap) return;
    const say = () => {
      last.current = Date.now();
      timer.current = null;
      setText(totalLaps ? `Lap ${lap} of ${totalLaps}` : `Lap ${lap}`);
    };
    if (timer.current) clearTimeout(timer.current);
    const wait = playing ? Math.max(0, ANNOUNCE_INTERVAL_MS - (Date.now() - last.current)) : 0;
    if (wait === 0) say();
    else timer.current = setTimeout(say, wait);
    return () => {
      if (timer.current) clearTimeout(timer.current);
      timer.current = null;
    };
  }, [lap, playing, totalLaps]);

  return (
    <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">
      {text}
    </p>
  );
}
