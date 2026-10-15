import { describe, expect, it } from "vitest";
import { groupSuggestions, searchHref, type SearchResponse } from "./search";

const driver = (n: number) => ({ slug: `d${n}`, name: `Driver ${n}`, code: null, number: null, nationality: "British" });

const data: SearchResponse = {
  drivers: Array.from({ length: 8 }, (_, i) => driver(i)),
  constructors: [{ slug: "ferrari", name: "Ferrari", nationality: "Italian" }],
  circuits: [],
  rounds: [{ year: 2024, round: 5, name: "Chinese Grand Prix", date: "2024-04-21" }],
};

describe("search suggestions", () => {
  it("groups by type, in order, with at most 5 per group", () => {
    const groups = groupSuggestions(data);
    expect(groups.map((g) => g.key)).toEqual(["drivers", "constructors", "rounds"]);
    expect(groups[0].items).toHaveLength(5);
    expect(groups[0].items[0]).toMatchObject({ href: "/drivers/d0", label: "Driver 0", detail: "British" });
    expect(groups[2].items[0]).toMatchObject({ href: "/seasons/2024/5", label: "2024 Chinese Grand Prix" });
  });

  it("can show everything on the results page", () => {
    expect(groupSuggestions(data, 100)[0].items).toHaveLength(8);
  });

  it("builds the full results link", () => {
    expect(searchHref(" räikkönen ")).toBe("/search?q=r%C3%A4ikk%C3%B6nen");
  });
});
