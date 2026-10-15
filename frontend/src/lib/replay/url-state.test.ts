import { describe, expect, it } from "vitest";
import { parseReplayParams, withReplayParams } from "./url-state";

describe("replay url state", () => {
  it("parses t and speed", () => {
    expect(parseReplayParams("?t=125&speed=20", 5000)).toEqual({ t: 125, speed: 20 });
  });
  it("falls back on invalid values and clamps t to the duration", () => {
    expect(parseReplayParams("?t=abc&speed=7", 5000)).toEqual({ t: 0, speed: 1 });
    expect(parseReplayParams("?t=-5", 5000).t).toBe(0);
    expect(parseReplayParams("?t=99999", 5000).t).toBe(5000);
    expect(parseReplayParams("", 5000)).toEqual({ t: 0, speed: 1 });
  });
  it("writes t and speed while keeping other parameters, omitting defaults", () => {
    expect(withReplayParams("?session=sprint", { t: 90.7, speed: 5 })).toBe("?session=sprint&t=90&speed=5");
    expect(withReplayParams("?t=10&speed=5&session=race", { t: 0, speed: 1 })).toBe("?session=race");
    expect(withReplayParams("", { t: 0, speed: 1 })).toBe("");
  });
});
