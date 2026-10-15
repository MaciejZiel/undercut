import { describe, expect, it, vi } from "vitest";
import { createApiClient } from "./client";

describe("api client", () => {
  it("calls GET /api/health/ on the given base URL", async () => {
    const fetchMock = vi.fn(async () => Response.json({ status: "ok" }));
    vi.stubGlobal("fetch", fetchMock);
    const { data } = await createApiClient("http://api.test").GET("/api/health/");
    expect(data).toEqual({ status: "ok" });
    const req = (fetchMock.mock.calls[0] as unknown as [Request])[0];
    expect(req.url).toBe("http://api.test/api/health/");
    vi.unstubAllGlobals();
  });
});
