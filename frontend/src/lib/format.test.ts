import { describe, expect, it } from "vitest";
import {
  describePositionChange,
  formatDate,
  formatGap,
  formatInteger,
  formatLapTime,
  formatLength,
  formatPoints,
  formatPosition,
  formatRaceTime,
  formatRaceGap,
  initials,
} from "./format";

describe("time formatting", () => {
  it("formats lap times with minutes only when needed", () => {
    expect(formatLapTime(83456)).toBe("1:23.456");
    expect(formatLapTime(59123)).toBe("59.123");
    expect(formatLapTime(60000)).toBe("1:00.000");
    expect(formatLapTime(5)).toBe("0.005");
  });

  it("formats the winner's total time with hours", () => {
    expect(formatRaceTime(5527123)).toBe("1:32:07.123");
    expect(formatRaceTime(3_600_000)).toBe("1:00:00.000");
    expect(formatRaceTime(754321)).toBe("12:34.321");
  });

  it("formats gaps with a plus sign", () => {
    expect(formatGap(5234)).toBe("+5.234");
    expect(formatGap(75000)).toBe("+1:15.000");
  });

  it("shows the winner's total time and the others' gap to it", () => {
    const winner = { position: 1, time_ms: 5527123, laps: 57, status: "Finished" };
    expect(formatRaceGap(winner, winner)).toBe("1:32:07.123");
    expect(formatRaceGap({ position: 2, time_ms: 5527123 + 5234, laps: 57, status: "Finished" }, winner)).toBe("+5.234");
    expect(formatRaceGap({ position: 3, time_ms: 5527123 + 75000, laps: 57, status: "Finished" }, winner)).toBe("+1:15.000");
  });

  it("shows laps down for lapped cars and nothing for retirements", () => {
    const winner = { position: 1, time_ms: 5527123, laps: 57, status: "Finished" };
    expect(formatRaceGap({ position: 12, time_ms: 5600000, laps: 56, status: "Lapped" }, winner)).toBe("+1 lap");
    expect(formatRaceGap({ position: 14, time_ms: 5600000, laps: 55, status: "Lapped" }, winner)).toBe("+2 laps");
    expect(formatRaceGap({ position: 18, time_ms: 5500000, laps: 40, status: "Retired" }, winner)).toBeNull();
    expect(formatRaceGap({ position: 19, time_ms: null, laps: 20, status: "Retired" }, winner)).toBeNull();
  });

  it("returns null for missing or invalid values, never zero", () => {
    expect(formatLapTime(null)).toBeNull();
    expect(formatLapTime(undefined)).toBeNull();
    expect(formatLapTime(-1)).toBeNull();
    expect(formatRaceTime(null)).toBeNull();
    expect(formatGap(null)).toBeNull();
    expect(formatRaceGap({ position: 1, time_ms: null, laps: 5, status: null }, undefined)).toBeNull();
  });

  it("keeps a real zero as a value", () => {
    expect(formatInteger(0)).toBe("0");
    expect(formatPoints(0)).toBe("0");
  });
});

describe("position change", () => {
  it("describes places gained, lost and unchanged", () => {
    expect(describePositionChange(3)).toMatchObject({ direction: "up", amount: 3, symbol: "▲", label: "Gained 3 places" });
    expect(describePositionChange(-1)).toMatchObject({ direction: "down", amount: 1, symbol: "▼", label: "Lost 1 place" });
    expect(describePositionChange(0)).toMatchObject({ direction: "same", label: "Position unchanged" });
  });

  it("is null when there is no data", () => {
    expect(describePositionChange(null)).toBeNull();
    expect(describePositionChange(undefined)).toBeNull();
  });
});

describe("other formatting", () => {
  it("formats points", () => {
    expect(formatPoints(25)).toBe("25");
    expect(formatPoints(12.5)).toBe("12.5");
    expect(formatPoints(1234.5)).toBe("1,234.5");
    expect(formatPoints(null)).toBeNull();
  });

  it("formats dates in UTC", () => {
    expect(formatDate("2023-03-05")).toBe("5 Mar 2023");
    expect(formatDate("2023-03-05T00:00:00Z")).toBe("5 Mar 2023");
    expect(formatDate(null)).toBeNull();
    expect(formatDate("garbage")).toBeNull();
  });

  it("formats circuit length", () => {
    expect(formatLength(5412)).toBe("5.412 km");
    expect(formatLength(null)).toBeNull();
  });

  it("shows retirement codes when there is no numeric position", () => {
    expect(formatPosition(4, "4")).toBe("4");
    expect(formatPosition(null, "R")).toBe("R");
    expect(formatPosition(null, null)).toBeNull();
  });

  it("builds initials", () => {
    expect(initials("Max Verstappen")).toBe("MV");
    expect(initials("Andrea de Cesaris")).toBe("AC");
    expect(initials("Ferrari")).toBe("FE");
    expect(initials("")).toBe("?");
  });
});
