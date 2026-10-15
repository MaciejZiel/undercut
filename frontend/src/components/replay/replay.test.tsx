import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PlaybackController, type Scheduler } from "@/lib/replay/controller";
import { makeDoc } from "@/lib/replay/test-doc";
import { lapStarts } from "@/lib/replay/frame";
import { Controls } from "./controls";
import { LapAnnouncer, ANNOUNCE_INTERVAL_MS } from "./lap-announcer";
import { handleReplayKey, ReplayView } from "./replay-view";
import { Timeline } from "./timeline";
import { TimingTable } from "./timing-table";

function manualScheduler() {
  let now = 0;
  const scheduler: Scheduler = { request: () => 1, cancel: () => {}, now: () => now };
  return { scheduler, set: (t: number) => (now = t) };
}

const doc = makeDoc();
const laps = lapStarts(doc);

function controllerAt(t = 0) {
  const m = manualScheduler();
  return new PlaybackController({ duration: 25, scheduler: m.scheduler, t });
}

function key(c: PlaybackController, k: string, extra: Partial<{ shiftKey: boolean; target: EventTarget | null }> = {}) {
  const preventDefault = vi.fn();
  const handled = handleReplayKey(c, {
    key: k,
    shiftKey: false,
    ctrlKey: false,
    metaKey: false,
    altKey: false,
    target: document.body,
    preventDefault,
    ...extra,
  });
  return { handled, preventDefault };
}

beforeEach(() => {
  vi.useFakeTimers();
});
afterEach(() => {
  vi.useRealTimers();
});

describe("TimingTable", () => {
  it("is a real table with a caption, column headers and row headers", () => {
    render(<TimingTable doc={doc} controller={controllerAt(0)} caption="Replay timing" />);
    const table = screen.getByRole("table", { name: "Replay timing" });
    expect(within(table).getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "Pos",
      "Driver",
      "Gap",
      "Int",
      "Tyre (age)",
      "Stops",
      "Lap",
    ]);
    expect(within(table).getAllByRole("rowheader")).toHaveLength(3);
  });

  it("shows gaps, tyre letter plus age and pit stops at the time", () => {
    render(<TimingTable doc={doc} controller={controllerAt(17)} caption="t" />);
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent("BBB");
    expect(rows[0]).toHaveTextContent("Leader");
    expect(rows[1]).toHaveTextContent("AAA");
    expect(rows[1]).toHaveTextContent("+1.500");
    expect(rows[1]).toHaveTextContent("M");
    expect(rows[1]).toHaveTextContent("Medium");
    expect(rows[0]).toHaveTextContent("Soft");
  });

  it("shows +1 LAP, a dash for a missing tyre and OUT for retired drivers", () => {
    render(<TimingTable doc={doc} controller={controllerAt(25)} caption="t" />);
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows[1]).toHaveTextContent("+1 LAP");
    expect(rows[2]).toHaveTextContent("OUT");
    expect(rows[2]).toHaveTextContent("—");
  });

  it("re-renders on a frame change, not on a time change inside the same frame", () => {
    const c = controllerAt(0);
    const spy = vi.spyOn(c, "getSnapshot");
    render(<TimingTable doc={doc} controller={c} caption="t" />);
    expect(screen.getAllByRole("row")[1]).toHaveTextContent("AAA");
    act(() => c.seek(2));
    expect(screen.getAllByRole("row")[1]).toHaveTextContent("AAA");
    act(() => c.seek(16));
    expect(screen.getAllByRole("row")[1]).toHaveTextContent("BBB");
    expect(spy).toHaveBeenCalled();
  });

  it("keeps a row element when it moves (reorder, not remount)", () => {
    const c = controllerAt(0);
    render(<TimingTable doc={doc} controller={c} caption="t" />);
    const before = document.querySelector('tr[data-id="1"]');
    act(() => c.seek(16));
    expect(document.querySelector('tr[data-id="1"]')).toBe(before);
  });
});

describe("FLIP reordering", () => {
  function withRowHeight(reduced: boolean) {
    Object.defineProperty(HTMLElement.prototype, "offsetHeight", { configurable: true, get: () => 40 });
    vi.stubGlobal("matchMedia", () => ({ matches: reduced }));
  }
  afterEach(() => {
    delete (HTMLElement.prototype as { offsetHeight?: number }).offsetHeight;
    vi.unstubAllGlobals();
  });

  it("offsets moved rows by transform, then transitions them in 200 ms or less", () => {
    withRowHeight(false);
    const c = controllerAt(10); // frame 2
    render(<TimingTable doc={doc} controller={c} caption="t" />);
    act(() => c.seek(15)); // frame 3: positions of drivers 1 and 2 swap
    const moved = document.querySelector<HTMLElement>('tr[data-id="1"]')!;
    expect(moved.style.transform).toBe("translateY(-40px)");
    expect(moved.style.transition).toBe("none");
    act(() => {
      vi.advanceTimersByTime(50);
    });
    expect(moved.style.transform).toBe("");
    expect(parseInt(moved.style.transition.match(/(\d+)ms/)![1], 10)).toBeLessThanOrEqual(200);
  });

  it("does not animate under prefers-reduced-motion or on a long seek", () => {
    withRowHeight(true);
    const c = controllerAt(10);
    render(<TimingTable doc={doc} controller={c} caption="t" />);
    act(() => c.seek(15));
    expect(document.querySelector<HTMLElement>('tr[data-id="1"]')!.style.transform).toBe("");
    vi.unstubAllGlobals();
    withRowHeight(false);
    act(() => c.seek(0));
    act(() => c.seek(25));
    expect(document.querySelector<HTMLElement>('tr[data-id="1"]')!.style.transform).toBe("");
  });
});

describe("Controls", () => {
  it("has labelled buttons and toggles play and pause", () => {
    const c = controllerAt(0);
    render(<Controls controller={c} laps={laps} totalLaps={2} duration={25} />);
    const play = screen.getByRole("button", { name: "Play" });
    fireEvent.click(play);
    expect(c.isPlaying).toBe(true);
    expect(screen.getByRole("button", { name: "Pause" })).toBeInTheDocument();
    c.destroy();
  });

  it("sets the speed with pressed state and jumps to a lap", () => {
    const c = controllerAt(0);
    render(<Controls controller={c} laps={laps} totalLaps={2} duration={25} />);
    fireEvent.click(screen.getByRole("button", { name: "Speed 20x" }));
    expect(c.speed).toBe(20);
    expect(screen.getByRole("button", { name: "Speed 20x" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Speed 1x" })).toHaveAttribute("aria-pressed", "false");
    fireEvent.change(screen.getByLabelText("Jump to lap"), { target: { value: "2" } });
    expect(c.t).toBe(15);
  });
});

describe("Timeline", () => {
  it("shows event markers that seek, and a slider labelled Timeline", () => {
    const c = controllerAt(0);
    render(<Timeline controller={c} duration={25} events={doc.events} laps={laps} />);
    const markers = within(screen.getByTestId("timeline-markers"));
    fireEvent.click(markers.getByRole("button", { name: /Red flag, lap 2/ }));
    expect(c.t).toBe(18);
    fireEvent.click(markers.getByRole("button", { name: /Safety car, lap 1/ }));
    expect(c.t).toBe(10);
    const slider = screen.getByRole("slider", { name: "Timeline" });
    fireEvent.change(slider, { target: { value: "7" } });
    expect(c.t).toBe(7);
    expect(markers.getByRole("button", { name: /Chequered flag/ })).toBeInTheDocument();
    expect(markers.getByRole("button", { name: /Race start/ })).toBeInTheDocument();
  });

  it("lists every event, pit stops included, as buttons", () => {
    render(<Timeline controller={controllerAt(0)} duration={25} events={doc.events} laps={laps} />);
    expect(screen.getByRole("button", { name: /BBB pit stop/ })).toBeInTheDocument();
  });
});

describe("LapAnnouncer", () => {
  it("announces politely and not on every lap change while playing", () => {
    const c = controllerAt(0);
    render(<LapAnnouncer controller={c} laps={laps} totalLaps={2} />);
    const region = screen.getByRole("status");
    expect(region).toHaveAttribute("aria-live", "polite");
    expect(region).toHaveTextContent("Lap 1 of 2");
    act(() => c.seek(16));
    expect(region).toHaveTextContent("Lap 2 of 2"); // paused: immediate
    act(() => c.seek(1));
    expect(region).toHaveTextContent("Lap 1 of 2");
    c.destroy();
  });

  it("throttles while playing", () => {
    const m = manualScheduler();
    const c = new PlaybackController({ duration: 25, scheduler: m.scheduler });
    render(<LapAnnouncer controller={c} laps={laps} totalLaps={2} />);
    const region = screen.getByRole("status");
    act(() => c.play());
    act(() => c.seek(16));
    expect(region).toHaveTextContent("Lap 1 of 2");
    act(() => {
      vi.advanceTimersByTime(ANNOUNCE_INTERVAL_MS + 10);
    });
    expect(region).toHaveTextContent("Lap 2 of 2");
  });
});

describe("keyboard", () => {
  it("space toggles, arrows seek, plus and minus change speed", () => {
    const c = controllerAt(12);
    expect(key(c, " ").handled).toBe(true);
    expect(c.isPlaying).toBe(true);
    key(c, " ");
    expect(c.isPlaying).toBe(false);
    key(c, "ArrowRight");
    expect(c.t).toBe(22);
    key(c, "ArrowLeft");
    expect(c.t).toBe(12);
    key(c, "ArrowRight", { shiftKey: true });
    expect(c.t).toBe(25);
    key(c, "+");
    expect(c.speed).toBe(5);
    key(c, "+");
    key(c, "+");
    key(c, "+");
    expect(c.speed).toBe(60);
    key(c, "-");
    expect(c.speed).toBe(20);
    c.destroy();
  });

  it("leaves space to buttons and arrows to sliders, and prevents default only when handled", () => {
    const c = controllerAt(5);
    const button = document.createElement("button");
    const input = document.createElement("input");
    expect(key(c, " ", { target: button }).handled).toBe(false);
    expect(key(c, "ArrowRight", { target: input }).handled).toBe(false);
    expect(c.t).toBe(5);
    const other = key(c, "x");
    expect(other.handled).toBe(false);
    expect(other.preventDefault).not.toHaveBeenCalled();
    expect(key(c, "ArrowRight").preventDefault).toHaveBeenCalled();
  });
});

describe("ReplayView", () => {
  it("renders the player and pauses when the tab is hidden", () => {
    render(<ReplayView doc={doc} caption="Replay timing" />);
    fireEvent.click(screen.getByRole("button", { name: "Play" }));
    expect(screen.getByRole("button", { name: "Pause" })).toBeInTheDocument();
    Object.defineProperty(document, "hidden", { configurable: true, get: () => true });
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(screen.getByRole("button", { name: "Play" })).toBeInTheDocument();
    Object.defineProperty(document, "hidden", { configurable: true, get: () => false });
  });

  it("writes t and speed to the URL on pause and restores them on mount", () => {
    window.history.replaceState(null, "", "/seasons/2024/1?view=replay&t=15&speed=5");
    const { unmount } = render(<ReplayView doc={doc} caption="c" />);
    expect(screen.getByRole("button", { name: "Speed 5x" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("slider", { name: "Timeline" })).toHaveValue("15");
    fireEvent.change(screen.getByRole("slider", { name: "Timeline" }), { target: { value: "20" } });
    expect(window.location.search).toBe("?view=replay&t=20&speed=5");
    unmount();
    window.history.replaceState(null, "", "/");
  });
});
