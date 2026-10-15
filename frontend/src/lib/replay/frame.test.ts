import { describe, expect, it } from "vitest";
import { frameAt, frameIndexAt, lapAtTime, lapStarts, lastFrameT, pitStopsAt, runIndex, runValue } from "./frame";
import { makeDoc } from "./test-doc";

describe("run encoded lookup", () => {
  it("finds the last entry at or before the index", () => {
    const at = [0, 3, 7];
    expect(runIndex(at, 0)).toBe(0);
    expect(runIndex(at, 2)).toBe(0);
    expect(runIndex(at, 3)).toBe(1);
    expect(runIndex(at, 6)).toBe(1);
    expect(runIndex(at, 99)).toBe(2);
    expect(runIndex(at, -1)).toBe(-1);
    expect(runIndex([], 4)).toBe(-1);
  });

  it("carries a value forward and returns null before the first entry", () => {
    const runs = { at: [2, 5], v: ["a", "b"] };
    expect(runValue(runs, 1)).toBeNull();
    expect(runValue(runs, 2)).toBe("a");
    expect(runValue(runs, 4)).toBe("a");
    expect(runValue(runs, 5)).toBe("b");
  });

  it("agrees with a linear scan on a long series", () => {
    const at = Array.from({ length: 500 }, (_, i) => i * 3);
    const runs = { at, v: at.map((_, i) => i) };
    for (let i = 0; i < 1600; i++) {
      const expected = Math.min(499, Math.floor(i / 3));
      expect(runValue(runs, i)).toBe(expected);
    }
  });
});

describe("frameIndexAt", () => {
  const doc = makeDoc();
  it("floors to the frame in effect and clamps", () => {
    expect(frameIndexAt(doc, 0)).toBe(0);
    expect(frameIndexAt(doc, 4.99)).toBe(0);
    expect(frameIndexAt(doc, 5)).toBe(1);
    expect(frameIndexAt(doc, 1000)).toBe(5);
    expect(frameIndexAt(doc, -3)).toBe(0);
    expect(frameIndexAt(doc, Number.NaN)).toBe(0);
    expect(lastFrameT(doc)).toBe(25);
  });
});

describe("frameAt", () => {
  const doc = makeDoc();

  it("orders rows by position and carries values forward", () => {
    const f = frameAt(doc, 0);
    expect(f.index).toBe(0);
    expect(f.rows.map((r) => r.driverId)).toEqual([1, 2, 3]);
    const f3 = frameAt(doc, 17);
    expect(f3.index).toBe(3);
    expect(f3.rows.map((r) => r.driverId)).toEqual([2, 1, 3]);
    expect(f3.rows[1]).toMatchObject({ gap: 1500, interval: 1500, lap: 2, tyre: "MEDIUM", tyreAge: 3 });
  });

  it("does not interpolate between frames", () => {
    expect(frameAt(doc, 4.9)).toEqual(frameAt(doc, 0.1));
  });

  it("puts drivers without a position last, in driver order", () => {
    const f = frameAt(doc, 20);
    expect(f.rows.map((r) => r.driverId)).toEqual([2, 1, 3]);
    expect(f.rows[2].position).toBeNull();
  });

  it("passes text gaps and nulls through", () => {
    expect(frameAt(doc, 25).rows[1].gap).toBe("+1 LAP");
    expect(frameAt(doc, 5).rows[2].interval).toBe("+1 LAP");
    expect(frameAt(doc, 0).rows[2].gap).toBeNull();
  });

  it("reports the leader lap, pit state and counted stops", () => {
    expect(frameAt(doc, 0).leaderLap).toBe(1);
    expect(frameAt(doc, 15).leaderLap).toBe(2);
    expect(frameAt(doc, 20).rows.find((r) => r.driverId === 1)).toMatchObject({ inPit: true, pitStops: 1 });
    expect(frameAt(doc, 25).rows.find((r) => r.driverId === 1)).toMatchObject({ inPit: false, pitStops: 1 });
    expect(frameAt(doc, 20).rows.find((r) => r.driverId === 3)?.pitStops).toBe(2);
  });

  it("counts pit stops as rising edges only", () => {
    expect(pitStopsAt({ at: [0, 1, 2, 3], v: [0, 1, 0, 1] }, 3)).toBe(2);
    expect(pitStopsAt({ at: [0, 1, 2, 3], v: [0, 1, 0, 1] }, 1)).toBe(1);
    expect(pitStopsAt({ at: [0], v: [1] }, 4)).toBe(1);
  });

  it("marks a driver retired from retired_t on", () => {
    expect(frameAt(doc, 19).rows.find((r) => r.driverId === 3)?.retired).toBe(false);
    expect(frameAt(doc, 20).rows.find((r) => r.driverId === 3)?.retired).toBe(true);
  });

  it("does O(drivers) work per call: lookups scale with drivers, not with frames", () => {
    const base = makeDoc();
    const frames = 20000;
    const big = makeDoc({
      frames: {
        step_s: 5,
        count: frames,
        t: Array.from({ length: frames }, (_, i) => i * 5),
        drivers: Array.from({ length: 20 }, (_, k) => {
          const src = base.frames.drivers[k % 3];
          const fill = <T,>(v: T) => Array.from({ length: frames }, () => v);
          return { ...src, pos: fill(k + 1), gap: fill(k * 1000), int: fill(1000) };
        }),
      },
      drivers: Array.from({ length: 20 }, (_, k) => ({ ...base.drivers[k % 3], driver_id: k + 1 })),
    });
    const f = frameAt(big, 49999);
    expect(f.rows).toHaveLength(20);
    expect(f.index).toBe(9999);
  });
});

describe("lap helpers", () => {
  it("derives the jump table from the earliest frame of each lap", () => {
    expect(lapStarts(makeDoc())).toEqual([
      { lap: 1, t: 0 },
      { lap: 2, t: 15 },
    ]);
  });

  it("finds the lap in progress at a time", () => {
    const laps = lapStarts(makeDoc());
    expect(lapAtTime(laps, 0)).toBe(1);
    expect(lapAtTime(laps, 14)).toBe(1);
    expect(lapAtTime(laps, 15)).toBe(2);
    expect(lapAtTime([], 5)).toBeNull();
  });
});
