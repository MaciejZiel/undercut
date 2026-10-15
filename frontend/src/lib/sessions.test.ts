import { describe, expect, it } from "vitest";
import { availableTabs, pickTab, tabHref } from "./sessions";

const weekend = [
  { type: "FP1", has_results: false },
  { type: "Q", has_results: true },
  { type: "SPRINT", has_results: true },
  { type: "RACE", has_results: true },
];

describe("session tabs", () => {
  it("shows only sessions that exist, race first", () => {
    expect(availableTabs(weekend).map((t) => t.key)).toEqual(["race", "sprint", "qualifying"]);
    expect(availableTabs([{ type: "Q", has_results: true }, { type: "RACE", has_results: true }]).map((t) => t.key)).toEqual([
      "race",
      "qualifying",
    ]);
    expect(availableTabs([])).toEqual([]);
  });

  it("opens the race by default when it has results", () => {
    const tabs = availableTabs(weekend);
    expect(pickTab(undefined, tabs, weekend)?.key).toBe("race");
  });

  it("falls back to the nearest session with results when the race has not happened", () => {
    const sessions = [
      { type: "Q", has_results: true },
      { type: "RACE", has_results: false },
    ];
    expect(pickTab(undefined, availableTabs(sessions), sessions)?.key).toBe("qualifying");
  });

  it("honours a requested tab only if the weekend has it", () => {
    const sessions = [{ type: "RACE", has_results: true }];
    const tabs = availableTabs(sessions);
    expect(pickTab("sprint", tabs, sessions)?.key).toBe("race");
    expect(pickTab("qualifying", availableTabs(weekend), weekend)?.key).toBe("qualifying");
    expect(pickTab(undefined, [], [])).toBeNull();
  });

  it("keeps the default tab on the plain round URL", () => {
    const tabs = availableTabs(weekend);
    const def = pickTab(undefined, tabs, weekend);
    expect(tabHref("/seasons/2024/5", tabs[0], def)).toBe("/seasons/2024/5");
    expect(tabHref("/seasons/2024/5", tabs[1], def)).toBe("/seasons/2024/5?session=sprint");
  });
});
