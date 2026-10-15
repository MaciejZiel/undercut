/**
 * Playback clock, deliberately free of React and of the DOM. The clock lives in plain fields
 * (never in React state): while playing, `t` is derived from the scheduler time, so reading it
 * is free. Subscribers are notified at most `uiHz` times per second while playing, and at once
 * on every control change (play, pause, seek, speed). The UI selects primitives from the
 * snapshot, so React only re-renders when a selected value changes (the frame index changes
 * every `step_s` of replay time, not every animation frame).
 */

export type Scheduler = {
  request: (cb: (now: number) => void) => number;
  cancel: (id: number) => void;
  /** Milliseconds, same time base as the callback argument. */
  now: () => number;
};

export type PlaybackSnapshot = {
  /** Replay time in seconds as of the last notification. */
  t: number;
  playing: boolean;
  speed: number;
  ended: boolean;
};

export type ControllerOptions = {
  duration: number;
  scheduler: Scheduler;
  t?: number;
  speed?: number;
  /** Cap of notifications per second while playing. */
  uiHz?: number;
};

export const browserScheduler: Scheduler = {
  request: (cb) => window.requestAnimationFrame(cb),
  cancel: (id) => window.cancelAnimationFrame(id),
  now: () => performance.now(),
};

export class PlaybackController {
  private readonly scheduler: Scheduler;
  private readonly duration: number;
  private readonly minGapMs: number;
  private anchorT: number;
  private anchorNow = 0;
  private playing = false;
  private speedValue: number;
  private rafId: number | null = null;
  private lastEmit = 0;
  private listeners = new Set<() => void>();
  private snap: PlaybackSnapshot;

  constructor(options: ControllerOptions) {
    this.scheduler = options.scheduler;
    this.duration = Math.max(0, options.duration);
    this.minGapMs = 1000 / Math.max(1, options.uiHz ?? 20);
    this.speedValue = options.speed && options.speed > 0 ? options.speed : 1;
    this.anchorT = this.clamp(options.t ?? 0);
    this.snap = this.makeSnapshot();
  }

  private clamp(t: number): number {
    if (!Number.isFinite(t)) return 0;
    return Math.min(this.duration, Math.max(0, t));
  }

  /** Live replay time in seconds. */
  get t(): number {
    if (!this.playing) return this.anchorT;
    return this.clamp(this.anchorT + ((this.scheduler.now() - this.anchorNow) / 1000) * this.speedValue);
  }

  get isPlaying(): boolean {
    return this.playing;
  }

  get speed(): number {
    return this.speedValue;
  }

  private makeSnapshot(): PlaybackSnapshot {
    const t = this.t;
    return { t, playing: this.playing, speed: this.speedValue, ended: t >= this.duration && this.duration > 0 };
  }

  /** Stable between notifications (useSyncExternalStore contract). */
  getSnapshot = (): PlaybackSnapshot => this.snap;

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  private emit(): void {
    this.snap = this.makeSnapshot();
    this.lastEmit = this.scheduler.now();
    for (const l of [...this.listeners]) l();
  }

  private rebase(): void {
    this.anchorT = this.t;
    this.anchorNow = this.scheduler.now();
  }

  play(): void {
    if (this.playing) return;
    if (this.anchorT >= this.duration) this.anchorT = 0; // replay from the start after the end
    this.playing = true;
    this.anchorNow = this.scheduler.now();
    this.schedule();
    this.emit();
  }

  pause(): void {
    if (!this.playing) return;
    this.rebase();
    this.playing = false;
    this.cancel();
    this.emit();
  }

  toggle(): void {
    if (this.playing) this.pause();
    else this.play();
  }

  seek(t: number): void {
    this.anchorT = this.clamp(t);
    this.anchorNow = this.scheduler.now();
    this.emit();
    if (this.playing && this.anchorT >= this.duration) this.finish();
  }

  seekBy(delta: number): void {
    this.seek(this.t + delta);
  }

  setSpeed(speed: number): void {
    if (!(speed > 0) || speed === this.speedValue) return;
    this.rebase();
    this.speedValue = speed;
    this.emit();
  }

  /** Stop the loop and drop listeners (unmount). */
  destroy(): void {
    this.cancel();
    this.playing = false;
    this.listeners.clear();
  }

  private schedule(): void {
    if (this.rafId === null) this.rafId = this.scheduler.request(this.tick);
  }

  private cancel(): void {
    if (this.rafId !== null) {
      this.scheduler.cancel(this.rafId);
      this.rafId = null;
    }
  }

  private finish(): void {
    this.anchorT = this.duration;
    this.playing = false;
    this.cancel();
    this.emit();
  }

  private tick = (now: number): void => {
    this.rafId = null;
    if (!this.playing) return;
    if (this.t >= this.duration) {
      this.finish();
      return;
    }
    if (now - this.lastEmit >= this.minGapMs) this.emit();
    this.schedule();
  };
}
