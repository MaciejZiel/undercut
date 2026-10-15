import { describe, expect, it } from "vitest";
import { contentSecurityPolicy } from "./security-headers";

describe("contentSecurityPolicy", () => {
  const policy = contentSecurityPolicy(false);
  const directive = (name: string) => policy.split("; ").find((d) => d.startsWith(`${name} `));

  it("locks everything to the own origin by default", () => {
    expect(directive("default-src")).toBe("default-src 'self'");
    expect(directive("connect-src")).toBe("connect-src 'self'");
  });

  it("forbids framing, plugins and foreign form targets", () => {
    expect(directive("frame-ancestors")).toBe("frame-ancestors 'none'");
    expect(directive("object-src")).toBe("object-src 'none'");
    expect(directive("form-action")).toBe("form-action 'self'");
    expect(directive("base-uri")).toBe("base-uri 'self'");
  });

  it("names exactly one foreign host: the OpenStreetMap embed", () => {
    expect(directive("frame-src")).toBe("frame-src https://www.openstreetmap.org");
    expect(policy.match(/https?:\/\/[^\s;]+/g)).toEqual(["https://www.openstreetmap.org"]);
    expect(policy).not.toContain("*");
  });

  it("allows eval only in development", () => {
    expect(policy).not.toContain("unsafe-eval");
    expect(contentSecurityPolicy(true)).toContain("'unsafe-eval'");
  });
});
