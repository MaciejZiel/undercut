import type { DriverFrames, ReplayDoc } from "./types";

/** Small synthetic document for tests: 3 drivers, 6 frames of 5 s. */
export function makeDoc(overrides: Partial<ReplayDoc> = {}): ReplayDoc {
  const count = 6;
  const drivers: DriverFrames[] = [
    {
      pos: [1, 1, 1, 2, 2, 2],
      gap: [0, 0, 0, 1500, 1800, "+1 LAP"],
      int: [0, 0, 0, 1500, 300, 400],
      lap: { at: [0, 3], v: [1, 2] },
      tyre: { at: [0], v: ["MEDIUM"] },
      age: { at: [0, 3], v: [2, 3] },
      pit: { at: [0, 4, 5], v: [0, 1, 0] },
    },
    {
      pos: [2, 2, 2, 1, 1, 1],
      gap: [900, 800, 700, 0, 0, 0],
      int: [900, 800, 700, 0, 0, 0],
      lap: { at: [0, 3], v: [1, 2] },
      tyre: { at: [0, 4], v: ["SOFT", "HARD"] },
      age: { at: [0, 4], v: [0, 0] },
      pit: { at: [0], v: [0] },
    },
    {
      pos: [null, 3, 3, 3, null, null],
      gap: [null, 75000, 76000, 77000, null, null],
      int: [null, "+1 LAP", null, 1000, null, null],
      lap: { at: [0], v: [1] },
      tyre: { at: [0], v: [null] },
      age: { at: [0], v: [null] },
      pit: { at: [0, 1, 2, 3, 4], v: [0, 1, 0, 1, 0] },
    },
  ];
  return {
    session: {
      year: 2024,
      round: 1,
      round_name: "Test GP",
      type: "RACE",
      status: "results_final",
      start: "2024-03-02T15:00:00Z",
      end: "2024-03-02T15:00:25Z",
      laps: 2,
      duration_s: 25,
    },
    drivers: [
      { driver_id: 1, code: "AAA", full_name: "Alpha A", constructor_name: "Team A", color_hex: "#ff0000", retired_t: null },
      { driver_id: 2, code: "BBB", full_name: "Beta B", constructor_name: "Team B", color_hex: null, retired_t: null },
      { driver_id: 3, code: "CCC", full_name: "Gamma C", constructor_name: "Team C", color_hex: "#00ff00", retired_t: 20 },
    ],
    frames: { step_s: 5, count, t: Array.from({ length: count }, (_, i) => i * 5), drivers },
    events: [
      { kind: "start", t: 0, lap: 1, label: "Race start", driver: null, end_t: null, end_lap: null },
      { kind: "pit", t: 12, lap: 1, label: "BBB pit stop", driver: "BBB", end_t: null, end_lap: null },
      { kind: "safety_car", t: 10, lap: 1, label: "Safety car", driver: null, end_t: 15, end_lap: 2 },
      { kind: "red_flag", t: 18, lap: 2, label: "Red flag", driver: null, end_t: null, end_lap: null },
      { kind: "chequered", t: 25, lap: 2, label: "Chequered flag", driver: null, end_t: null, end_lap: null },
    ],
    ...overrides,
  };
}
