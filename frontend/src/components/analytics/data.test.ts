import { describe, expect, it } from "vitest";
import {
  bestOf,
  compoundLetter,
  compoundStyle,
  dashedDrivers,
  defaultLapDrivers,
  finishingOrder,
  formatSeconds,
  lapMatrix,
  methodLabel,
  neutralisationBands,
  positionPairs,
  stintRows,
  stintSegments,
  teamColor,
  totalLaps,
  type Laps,
  type Positions,
  type Stints,
} from "./data";
import { buildPositionsOption } from "./options";
import { pickView, viewHref, visibleViews } from "./round-views";
import { filterMessages } from "./race-control-view";

const driver = (code: string, constructor_id: number, positions: (number | null)[], pit_laps: number[] = []) => ({
  driver_id: 1,
  code,
  full_name: code,
  constructor_id,
  constructor_name: "T" + constructor_id,
  color_hex: constructor_id === 1 ? "#ff0000" : null,
  positions,
  pit_laps,
});

const positions: Positions = {
  session: { year: 2024, round: 1, round_name: "X", type: "RACE", status: "results_final" },
  laps: [1, 2, 3],
  drivers: [driver("AAA", 1, [2, 2, null]), driver("BBB", 1, [1, 1, 1], [2]), driver("CCC", 2, [3, 3, 2])],
  neutralisations: [{ kind: "SC", start_lap: 2, end_lap: 3 }],
};

const tokens = { fg: "#000", muted: "#777", line: "#ccc", surface: "#fff", accent: "#00f", palette: ["#111"] };

describe("positions helpers", () => {
  it("orders by last known position", () => {
    expect(finishingOrder(positions)).toEqual(["BBB", "AAA", "CCC"]);
    expect(defaultLapDrivers(positions, 2)).toEqual(["BBB", "AAA"]);
  });
  it("keeps missing positions as null", () => {
    expect(positionPairs([1, 2, 3], [1, null])).toEqual([[1, 1], [2, null], [3, null]]);
  });
  it("builds padded SC/VSC bands and skips invalid ones", () => {
    expect(
      neutralisationBands([
        { kind: "SC", start_lap: 5, end_lap: 7 },
        { kind: "VSC", start_lap: 9, end_lap: 9 },
        { kind: "SC", start_lap: 12, end_lap: 10 },
      ]),
    ).toEqual([
      { kind: "SC", from: 4.5, to: 7.5 },
      { kind: "VSC", from: 8.5, to: 9.5 },
    ]);
  });
  it("dashes the second teammate", () => {
    expect([...dashedDrivers(positions.drivers)]).toEqual(["BBB"]);
  });
  it("uses a neutral colour for null or malformed hex", () => {
    expect(teamColor("#00ff00", "#777")).toBe("#00ff00");
    expect(teamColor(null, "#777")).toBe("#777");
    expect(teamColor("red", "#777")).toBe("#777");
  });
});

describe("buildPositionsOption", () => {
  it("inverts y, draws pit dots, bands and fades non highlighted lines", () => {
    const o = buildPositionsOption(positions, "BBB", tokens) as unknown as Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
    expect(o.yAxis.inverse).toBe(true);
    expect(o.series).toHaveLength(3);
    const b = o.series[1];
    expect(b.data[1].symbol).toBe("circle");
    expect(b.lineStyle.opacity).toBe(1);
    expect(o.series[0].lineStyle.opacity).toBeLessThan(0.5);
    expect(o.series[0].color).toBe("#ff0000");
    expect(o.series[2].color).toBe("#777");
    expect(o.series[0].markArea.data).toHaveLength(1);
    expect(o.series[1].markArea).toBeUndefined();
  });
});

describe("stints", () => {
  const stint = (n: number, c: string, l: string, s: number | null, e: number | null, laps: number | null) => ({
    stint_number: n, compound: c as "SOFT", compound_letter: l as "S", lap_start: s, lap_end: e, laps, tyre_age_at_start: 0,
  });
  it("computes widths as share of the race", () => {
    const seg = stintSegments([stint(2, "HARD", "H", 21, 50, 30), stint(1, "SOFT", "S", 1, 20, 20)], 50);
    expect(seg.map((s) => s.letter)).toEqual(["S", "H"]);
    expect(seg[0]).toMatchObject({ left: 0, width: 40, lapStart: 1, lapEnd: 20 });
    expect(seg[1]).toMatchObject({ left: 40, width: 60 });
  });
  it("falls back to cumulative laps and skips empty stints", () => {
    const seg = stintSegments([stint(1, "SOFT", "S", null, null, 10), stint(2, "MEDIUM", "M", null, null, 0), stint(3, "HARD", "H", null, null, 10)], 20);
    expect(seg).toHaveLength(2);
    expect(seg[1].left).toBe(50);
    expect(stintSegments([], 0)).toEqual([]);
  });
  it("orders rows by finishing position and finds total laps", () => {
    const d = (code: string, position: number | null, laps: number) => ({
      ...driver(code, 1, []), position, stints: [stint(1, "SOFT", "S", 1, laps, laps)],
    });
    const data = { session: positions.session, drivers: [d("X", null, 40), d("Y", 2, 57), d("Z", 1, 57)] } as unknown as Stints;
    expect(stintRows(data).map((x) => x.code)).toEqual(["Z", "Y", "X"]);
    expect(totalLaps(data)).toBe(57);
  });
  it("maps compounds to letters and styles", () => {
    expect(compoundLetter("INTERMEDIATE")).toBe("I");
    expect(compoundLetter("soft")).toBe("S");
    expect(compoundLetter(null)).toBe("?");
    expect(compoundStyle("nope").label).toBe("Unknown");
  });
});

describe("laps and formatting", () => {
  it("builds the lap matrix", () => {
    const data = {
      drivers: [
        { lap_numbers: [1, 2], duration_ms: [90000, null] },
        { lap_numbers: [2, 3], duration_ms: [91000, 92000] },
      ],
    } as unknown as Laps;
    expect(lapMatrix(data)).toEqual([
      { lap: 1, times: [90000, null] },
      { lap: 2, times: [null, 91000] },
      { lap: 3, times: [null, 92000] },
    ]);
  });
  it("finds the best sector and formats seconds", () => {
    expect(bestOf([null, 30100, 29900])).toBe(29900);
    expect(bestOf([null])).toBeNull();
    expect(formatSeconds(2345)).toBe("2.345 s");
    expect(formatSeconds(null)).toBeNull();
    expect(methodLabel("lane_duration")).toBe("pit lane duration");
    expect(methodLabel("stop_duration")).toBe("stop duration");
  });
});

describe("round views", () => {
  it("hides analytics views before 2023", () => {
    expect(visibleViews(2022).map((v) => v.key)).toEqual(["results"]);
    expect(visibleViews(2023).map((v) => v.key)).toEqual(["results", "analysis", "strategy", "replay"]);
    expect(pickView("analysis", 2021)).toBe("results");
    expect(pickView("strategy", 2024)).toBe("strategy");
    expect(pickView("bogus", 2024)).toBe("results");
  });
  it("builds hrefs without defaults", () => {
    expect(viewHref("/r", {})).toBe("/r");
    expect(viewHref("/r", { session: "sprint", view: "analysis" })).toBe("/r?session=sprint&view=analysis");
    expect(viewHref("/r", { view: "results" })).toBe("/r");
  });
  it("filters race control messages", () => {
    const m = [{ category: "Flag" }, { category: "SafetyCar" }] as never[];
    expect(filterMessages(m, null)).toHaveLength(2);
    expect(filterMessages(m, "Flag")).toHaveLength(1);
  });
});
