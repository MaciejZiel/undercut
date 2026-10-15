import { describe, expect, it } from "vitest";
import { codeFor, flagEmoji, flagFor, KNOWN_NATIONALITIES } from "./nationality";

describe("nationality to flag", () => {
  it("maps demonyms case-insensitively", () => {
    expect(codeFor("British")).toBe("GB");
    expect(codeFor("  german ")).toBe("DE");
    expect(codeFor("Monegasque")).toBe("MC");
  });

  it("maps country names used by circuits", () => {
    expect(codeFor("UK")).toBe("GB");
    expect(codeFor("UAE")).toBe("AE");
    expect(codeFor("USA")).toBe("US");
  });

  it("converts a code to a flag emoji", () => {
    expect(flagEmoji("PL")).toBe("🇵🇱");
    expect(flagFor("Polish")).toBe("🇵🇱");
  });

  it("returns null for unknown or missing values", () => {
    expect(flagFor("Atlantean")).toBeNull();
    expect(flagFor(null)).toBeNull();
    expect(flagFor("")).toBeNull();
  });

  it("offers a sorted list of suggestions", () => {
    expect(KNOWN_NATIONALITIES).toContain("British");
    expect(KNOWN_NATIONALITIES).toEqual([...KNOWN_NATIONALITIES].sort());
  });
});
