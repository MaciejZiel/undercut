import { describe, expect, it } from "vitest";
import { buildHref, first, isSlug, nextOrdering, param, parseChoice, parseIntParam, parseSort, resolveSeasonFilter } from "./url";

describe("url helpers", () => {
  it("reads the first non-empty value", () => {
    expect(first(" abc ")).toBe("abc");
    expect(first(["x", "y"])).toBe("x");
    expect(first("")).toBeUndefined();
    expect(first(undefined)).toBeUndefined();
  });

  it("ignores non-string values from prototype lookups", () => {
    const sp: Record<string, string | undefined> = {};
    expect(param(sp, "constructor")).toBeUndefined();
    expect(first(sp.constructor as never)).toBeUndefined();
  });

  it("parses bounded integers", () => {
    expect(parseIntParam("1988", { min: 1950, max: 2100 })).toBe(1988);
    expect(parseIntParam("1900", { min: 1950 })).toBeUndefined();
    expect(parseIntParam("12abc")).toBeUndefined();
    expect(parseIntParam("-3")).toBeUndefined();
    expect(parseIntParam("0")).toBeUndefined();
  });

  it("accepts only allowed choices", () => {
    expect(parseChoice("-wins", ["wins", "-wins"] as const, "wins")).toBe("-wins");
    expect(parseChoice("drop table", ["wins", "-wins"] as const, "wins")).toBe("wins");
  });

  it("builds hrefs without empty values", () => {
    expect(buildHref("/drivers", { season: 1988, q: "", nationality: undefined, page: 2 })).toBe("/drivers?season=1988&page=2");
    expect(buildHref("/drivers", {})).toBe("/drivers");
    expect(buildHref("/search", { q: "räikkönen & co" })).toBe("/search?q=r%C3%A4ikk%C3%B6nen+%26+co");
  });

  it("toggles sorting", () => {
    expect(parseSort("-wins")).toEqual({ field: "wins", desc: true });
    expect(nextOrdering("family_name", "wins", true)).toBe("-wins");
    expect(nextOrdering("family_name", "family_name", false)).toBe("-family_name");
    expect(nextOrdering("-family_name", "family_name", false)).toBe("family_name");
    expect(nextOrdering("wins", "name", false)).toBe("name");
  });

  it("validates slugs", () => {
    expect(isSlug("max_verstappen")).toBe(true);
    expect(isSlug("red-bull")).toBe(true);
    expect(isSlug("../etc")).toBe(false);
    expect(isSlug("")).toBe(false);
  });
});

describe("resolveSeasonFilter", () => {
  const base = { latest: 2026, hasOtherFilters: false };

  it("defaults to the latest season when nothing is filtered", () => {
    expect(resolveSeasonFilter({ ...base, season: undefined })).toEqual({ season: 2026, defaulted: true });
  });

  it("keeps an explicit season", () => {
    expect(resolveSeasonFilter({ ...base, season: "1988" })).toEqual({ season: 1988, defaulted: false });
  });

  it("shows everyone for season=all", () => {
    expect(resolveSeasonFilter({ ...base, season: "all" })).toEqual({ season: undefined, defaulted: false });
  });

  it("does not default when another filter is set", () => {
    expect(resolveSeasonFilter({ ...base, season: undefined, hasOtherFilters: true })).toEqual({
      season: undefined,
      defaulted: false,
    });
  });

  it("ignores junk and falls back to the default", () => {
    expect(resolveSeasonFilter({ ...base, season: "abc" })).toEqual({ season: 2026, defaulted: true });
  });

  it("falls back to everyone when the latest season is unknown", () => {
    expect(resolveSeasonFilter({ ...base, latest: undefined, season: undefined })).toEqual({
      season: undefined,
      defaulted: false,
    });
  });
});
