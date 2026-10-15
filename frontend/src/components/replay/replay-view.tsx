"use client";

import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
import { browserScheduler, PlaybackController } from "@/lib/replay/controller";
import { SPEEDS, type Speed } from "@/lib/replay/format";
import { lapStarts, lastFrameT } from "@/lib/replay/frame";
import type { ReplayDoc } from "@/lib/replay/types";
import { parseReplayParams, withReplayParams } from "@/lib/replay/url-state";
import { Controls, SEEK_STEP_S } from "./controls";
import { LapAnnouncer } from "./lap-announcer";
import { Timeline } from "./timeline";
import { TimingTable } from "./timing-table";

const URL_WRITE_INTERVAL_MS = 2000;
const UI_HZ = 20;
const BIG_SEEK_S = 60;

/** Keys the player handles itself. Native widgets keep their own arrow and space behaviour. */
export function handleReplayKey(
  controller: PlaybackController,
  e: Pick<KeyboardEvent, "key" | "shiftKey" | "preventDefault" | "ctrlKey" | "metaKey" | "altKey"> & {
    target: EventTarget | null;
  },
): boolean {
  if (e.ctrlKey || e.metaKey || e.altKey) return false;
  const tag = e.target instanceof HTMLElement ? e.target.tagName : "";
  const native = tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA";
  const interactive = native || tag === "BUTTON" || tag === "A" || tag === "SUMMARY";
  let handled = true;
  switch (e.key) {
    case " ":
      if (interactive) return false;
      controller.toggle();
      break;
    case "ArrowLeft":
    case "ArrowRight":
      if (native) return false;
      controller.seekBy((e.key === "ArrowLeft" ? -1 : 1) * (e.shiftKey ? BIG_SEEK_S : SEEK_STEP_S));
      break;
    case "+":
    case "=":
    case "-":
    case "_": {
      const at = SPEEDS.indexOf(controller.speed as (typeof SPEEDS)[number]);
      const up = e.key === "+" || e.key === "=";
      const next = SPEEDS[Math.min(SPEEDS.length - 1, Math.max(0, (at < 0 ? 0 : at) + (up ? 1 : -1)))];
      controller.setSpeed(next);
      break;
    }
    default:
      handled = false;
  }
  if (handled) e.preventDefault();
  return handled;
}

export function ReplayView({ doc, caption }: { doc: ReplayDoc; caption: string }) {
  const duration = useMemo(() => lastFrameT(doc), [doc]);
  const laps = useMemo(() => lapStarts(doc), [doc]);
  const [controller] = useState(() => {
    const initial = parseReplayParams(typeof window === "undefined" ? "" : window.location.search, duration);
    return new PlaybackController({
      duration,
      scheduler: browserScheduler,
      t: initial.t,
      speed: initial.speed,
      uiHz: UI_HZ,
    });
  });

  useEffect(() => () => controller.destroy(), [controller]);

  // Pause when the tab is hidden: the clock would otherwise jump on return.
  useEffect(() => {
    const onVisibility = () => {
      if (document.hidden) controller.pause();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [controller]);

  // URL: ?t= and ?speed=. Written at once on pause, seek-by-controls and speed change, and at most every 2 s while playing.
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | null = null;
    let lastSpeed = controller.speed;
    let lastPlaying = controller.isPlaying;
    const write = () => {
      timer = null;
      const url = new URL(window.location.href);
      const search = withReplayParams(url.search, { t: controller.t, speed: controller.speed as Speed });
      if (search !== url.search) window.history.replaceState(window.history.state, "", `${url.pathname}${search}${url.hash}`);
    };
    const off = controller.subscribe(() => {
      const snap = controller.getSnapshot();
      const changed = snap.speed !== lastSpeed || snap.playing !== lastPlaying;
      lastSpeed = snap.speed;
      lastPlaying = snap.playing;
      if (!snap.playing || changed) {
        if (timer) clearTimeout(timer);
        write();
      } else if (!timer) {
        timer = setTimeout(write, URL_WRITE_INTERVAL_MS);
      }
    });
    return () => {
      off();
      if (timer) clearTimeout(timer);
    };
  }, [controller]);

  return (
    <section
      aria-label="Session replay"
      tabIndex={0}
      onKeyDown={(e) => handleReplayKey(controller, e)}
      className="grid gap-4 rounded-sm outline-offset-4"
    >
      <Controls controller={controller} laps={laps} totalLaps={doc.session.laps || null} duration={duration} />
      <Timeline controller={controller} duration={duration} events={doc.events} laps={laps} />
      <LapAnnouncer controller={controller} laps={laps} totalLaps={doc.session.laps || null} />
      <TimingTable doc={doc} controller={controller} caption={caption} />
      <p className="text-sm text-muted">
        Keyboard (focus this area): Space play or pause, Left and Right arrows jump 10 s (Shift 60 s), + and - change the speed.
        Positions, gaps and tyres are shown as recorded every {doc.frames.step_s} s.
      </p>
    </section>
  );
}
