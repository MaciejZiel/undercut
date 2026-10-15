import { describe, expect, it } from "vitest";
import { compoundInfo, formatClock, formatReplayGap } from "./format";

describe("formatReplayGap", () => {
  it("formats milliseconds as +s.mmm and +m:ss.mmm", () => {
    expect(formatReplayGap(12345)).toBe("+12.345");
    expect(formatReplayGap(900)).toBe("+0.900");
    expect(formatReplayGap(75000)).toBe("+1:15.000");
    expect(formatReplayGap(0)).toBe("+0.000");
  });
  it("keeps text such as +1 LAP and shows a dash for missing values", () => {
    expect(formatReplayGap("+1 LAP")).toBe("+1 LAP");
    expect(formatReplayGap(null)).toBe("—");
    expect(formatReplayGap("  ")).toBe("—");
    expect(formatReplayGap(-5)).toBe("—");
    expect(formatReplayGap(Number.NaN)).toBe("—");
  });
});

describe("compoundInfo", () => {
  it("maps compounds to a letter and a name", () => {
    expect(["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"].map((c) => compoundInfo(c)?.letter)).toEqual([
      "S",
      "M",
      "H",
      "I",
      "W",
    ]);
    expect(compoundInfo("soft")?.name).toBe("Soft");
  });
  it("returns null for unknown or missing compounds", () => {
    expect(compoundInfo(null)).toBeNull();
    expect(compoundInfo("UNKNOWN")).toBeNull();
  });
});

describe("formatClock", () => {
  it("formats m:ss and h:mm:ss", () => {
    expect(formatClock(0)).toBe("0:00");
    expect(formatClock(65.9)).toBe("1:05");
    expect(formatClock(3723)).toBe("1:02:03");
    expect(formatClock(-4)).toBe("0:00");
  });
});
