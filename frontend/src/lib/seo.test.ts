import { afterEach, describe, expect, it, vi } from "vitest";
import { absoluteUrl, pageMetadata, siteUrl } from "./seo";

afterEach(() => vi.unstubAllEnvs());

describe("seo helpers", () => {
  it("defaults the site URL and strips trailing slashes from the override", () => {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "");
    expect(siteUrl()).toBe("https://undercut.maciejzielinski.dev");
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://example.test//");
    expect(absoluteUrl("/about")).toBe("https://example.test/about");
  });

  it("builds canonical and Open Graph fields", () => {
    const m = pageMetadata({ title: "Drivers", description: "d", path: "/drivers" });
    expect(m.alternates?.canonical).toBe("/drivers");
    expect(m.openGraph).toMatchObject({ title: "Drivers | Undercut", url: "/drivers", siteName: "Undercut" });
  });
});
