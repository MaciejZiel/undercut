import { afterEach, describe, expect, it, vi } from "vitest";
import { createApiClient, resolveBaseUrl } from "./client";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("api client", () => {
  it("calls the typed season list endpoint on the given base URL", async () => {
    const fetchMock = vi.fn(async () => Response.json({ count: 0, results: [] }));
    vi.stubGlobal("fetch", fetchMock);
    const { data } = await createApiClient("http://api.test").GET("/api/v1/seasons/", {
      params: { query: { page_size: 100 } },
    });
    expect(data).toEqual({ count: 0, results: [] });
    const req = (fetchMock.mock.calls[0] as unknown as [Request])[0];
    expect(req.url).toBe("http://api.test/api/v1/seasons/?page_size=100");
  });

  it("falls back to the local backend when API_INTERNAL_URL is unset", () => {
    vi.stubGlobal("window", undefined);
    vi.stubEnv("API_INTERNAL_URL", "");
    delete process.env.API_INTERNAL_URL;
    expect(resolveBaseUrl()).toBe("http://127.0.0.1:8000");
    vi.stubEnv("API_INTERNAL_URL", "http://backend:9000");
    expect(resolveBaseUrl()).toBe("http://backend:9000");
  });
});

describe("internal token", () => {
  const sent = async () => {
    const fetchMock = vi.fn(async () => Response.json({ count: 0, results: [] }));
    vi.stubGlobal("fetch", fetchMock);
    await createApiClient("http://api.test").GET("/api/v1/seasons/", {});
    return (fetchMock.mock.calls[0] as unknown as [Request])[0].headers.get("x-internal-token");
  };

  it("is sent by the server-side client so SSR is not rate limited as one anonymous visitor", async () => {
    vi.stubGlobal("window", undefined);
    vi.stubEnv("INTERNAL_API_TOKEN", "server-secret");
    expect(await sent()).toBe("server-secret");
  });

  it("is omitted when no token is configured", async () => {
    vi.stubGlobal("window", undefined);
    vi.stubEnv("INTERNAL_API_TOKEN", "");
    expect(await sent()).toBeNull();
  });

  it("never reaches the browser, even if the variable exists", async () => {
    vi.stubEnv("INTERNAL_API_TOKEN", "server-secret"); // jsdom: window is defined
    expect(await sent()).toBeNull();
  });
});
