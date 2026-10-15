import { describe, expect, it, vi } from "vitest";
import { PlaybackController, type Scheduler } from "./controller";

/** Manual scheduler: time only moves when the test advances it. */
function manual() {
  let now = 0;
  let id = 0;
  const pending = new Map<number, (n: number) => void>();
  const scheduler: Scheduler = {
    request: (cb) => {
      pending.set(++id, cb);
      return id;
    },
    cancel: (i) => void pending.delete(i),
    now: () => now,
  };
  /** Advance in 16 ms frames; guarded so a bug cannot loop forever. */
  const advance = (ms: number) => {
    const end = now + ms;
    let guard = 0;
    while (now < end && guard++ < 100_000) {
      now = Math.min(end, now + 16);
      const cbs = [...pending.entries()];
      pending.clear();
      for (const [, cb] of cbs) cb(now);
    }
  };
  return { scheduler, advance, pendingCount: () => pending.size };
}

describe("PlaybackController", () => {
  it("advances the clock by speed while playing", () => {
    const m = manual();
    const c = new PlaybackController({ duration: 1000, scheduler: m.scheduler, speed: 20 });
    c.play();
    m.advance(1000);
    expect(c.t).toBeCloseTo(20, 0);
    c.pause();
    const frozen = c.t;
    m.advance(500);
    expect(c.t).toBe(frozen);
  });

  it("changes speed without a jump in time", () => {
    const m = manual();
    const c = new PlaybackController({ duration: 1000, scheduler: m.scheduler });
    c.play();
    m.advance(2000);
    const before = c.t;
    c.setSpeed(60);
    expect(c.t).toBeCloseTo(before, 1);
    m.advance(1000);
    expect(c.t).toBeCloseTo(before + 60, 0);
  });

  it("seeks, clamps and keeps playing from the new point", () => {
    const m = manual();
    const c = new PlaybackController({ duration: 100, scheduler: m.scheduler });
    c.seek(-5);
    expect(c.t).toBe(0);
    c.seek(40);
    c.play();
    m.advance(1000);
    expect(c.t).toBeCloseTo(41, 0);
    c.seekBy(-10);
    expect(c.t).toBeCloseTo(31, 0);
  });

  it("stops at the end and replays from the start on the next play", () => {
    const m = manual();
    const c = new PlaybackController({ duration: 10, scheduler: m.scheduler, speed: 5 });
    c.play();
    m.advance(5000);
    expect(c.isPlaying).toBe(false);
    expect(c.t).toBe(10);
    expect(c.getSnapshot().ended).toBe(true);
    expect(m.pendingCount()).toBe(0);
    c.play();
    expect(c.t).toBe(0);
    expect(c.isPlaying).toBe(true);
  });

  it("caps notifications while playing but notifies control changes at once", () => {
    const m = manual();
    const c = new PlaybackController({ duration: 10_000, scheduler: m.scheduler, uiHz: 15 });
    const listener = vi.fn();
    c.subscribe(listener);
    c.play();
    expect(listener).toHaveBeenCalledTimes(1);
    m.advance(1000); // about 62 animation frames
    const calls = listener.mock.calls.length - 1;
    expect(calls).toBeGreaterThanOrEqual(10);
    expect(calls).toBeLessThanOrEqual(16);
    c.setSpeed(5);
    expect(listener.mock.calls.length - 1).toBe(calls + 1);
  });

  it("keeps the snapshot object stable between notifications", () => {
    const m = manual();
    const c = new PlaybackController({ duration: 100, scheduler: m.scheduler });
    const a = c.getSnapshot();
    expect(c.getSnapshot()).toBe(a);
    c.seek(10);
    expect(c.getSnapshot()).not.toBe(a);
    expect(c.getSnapshot().t).toBe(10);
  });

  it("runs no loop while paused and cleans up on destroy", () => {
    const m = manual();
    const c = new PlaybackController({ duration: 100, scheduler: m.scheduler });
    expect(m.pendingCount()).toBe(0);
    c.play();
    expect(m.pendingCount()).toBe(1);
    c.pause();
    expect(m.pendingCount()).toBe(0);
    c.play();
    const l = vi.fn();
    c.subscribe(l);
    c.destroy();
    expect(m.pendingCount()).toBe(0);
    m.advance(100);
    expect(l).not.toHaveBeenCalled();
  });

  it("ignores invalid speeds and unsubscribes listeners", () => {
    const m = manual();
    const c = new PlaybackController({ duration: 100, scheduler: m.scheduler });
    const l = vi.fn();
    const off = c.subscribe(l);
    c.setSpeed(0);
    c.setSpeed(Number.NaN);
    expect(c.speed).toBe(1);
    expect(l).not.toHaveBeenCalled();
    off();
    c.seek(5);
    expect(l).not.toHaveBeenCalled();
  });
});
