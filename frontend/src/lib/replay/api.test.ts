import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchReplay, ReplayLoadError, replayKey } from "./api";
import { makeDoc } from "./test-doc";

afterEach(() => vi.unstubAllGlobals());

describe("fetchReplay", () => {
  it("requests the typed endpoint with session and step", async () => {
    const fetchMock = vi.fn(async () => Response.json(makeDoc()));
    vi.stubGlobal("fetch", fetchMock);
    const doc = await fetchReplay(2024, 5, "SPRINT", 5, "http://api.test");
    expect(doc.drivers).toHaveLength(3);
    const req = (fetchMock.mock.calls[0] as unknown as [Request])[0];
    expect(req.url).toBe("http://api.test/api/v1/rounds/2024/5/replay/?session=SPRINT&step=5");
  });

  it("throws a typed error with the status for a 404", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ detail: "x" }, { status: 404 })));
    const err = await fetchReplay(2024, 5, "RACE", 5, "http://api.test").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ReplayLoadError);
    expect((err as ReplayLoadError).status).toBe(404);
  });

  it("keys the cache by round, session and step", () => {
    expect(replayKey(2024, 5, "RACE")).toEqual(["replay", 2024, 5, "RACE", 5]);
  });
});
