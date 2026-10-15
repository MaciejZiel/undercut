import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { revalidateTag } = vi.hoisted(() => ({ revalidateTag: vi.fn() }));
vi.mock("next/cache", () => ({ revalidateTag }));

import { POST } from "./route";

function call(body: unknown, headers: Record<string, string> = { "x-revalidate-secret": "s3cret" }, raw?: string) {
  return POST(
    new Request("http://localhost/_internal/revalidate", {
      method: "POST",
      headers: { "content-type": "application/json", ...headers },
      body: raw ?? JSON.stringify(body),
    }),
  );
}

beforeEach(() => {
  vi.stubEnv("REVALIDATE_SECRET", "s3cret");
  revalidateTag.mockReset();
});
afterEach(() => vi.unstubAllEnvs());

describe("POST /_internal/revalidate", () => {
  it("purges each tag and reports them", async () => {
    const res = await call({ tags: ["drivers", "round:2024-5", "drivers"] });
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ revalidated: ["drivers", "round:2024-5"] });
    expect(revalidateTag).toHaveBeenCalledTimes(2);
    expect(revalidateTag).toHaveBeenCalledWith("round:2024-5", { expire: 0 });
  });

  it("rejects a missing or wrong secret", async () => {
    expect((await call({ tags: ["drivers"] }, {})).status).toBe(401);
    expect((await call({ tags: ["drivers"] }, { "x-revalidate-secret": "nope" })).status).toBe(401);
    expect((await call({ tags: ["drivers"] }, { "x-revalidate-secret": "s3cret-longer" })).status).toBe(401);
    expect(revalidateTag).not.toHaveBeenCalled();
  });

  it("fails closed when no secret is configured", async () => {
    vi.stubEnv("REVALIDATE_SECRET", "");
    const res = await call({ tags: ["drivers"] }, { "x-revalidate-secret": "" });
    expect(res.status).toBe(503);
    expect(revalidateTag).not.toHaveBeenCalled();
  });

  it.each([
    [{}],
    [{ tags: [] }],
    [{ tags: "drivers" }],
    [{ tags: [1] }],
    [{ tags: ["has space"] }],
    [{ tags: ["Drivers"] }],
    [{ tags: Array.from({ length: 101 }, (_, i) => `t${i}`.replace(/\d/g, "x")) }],
  ])("rejects an invalid body %j", async (body) => {
    expect((await call(body)).status).toBe(400);
    expect(revalidateTag).not.toHaveBeenCalled();
  });

  it("rejects a body that is not JSON", async () => {
    expect((await call(undefined, undefined, "not json")).status).toBe(400);
  });
});
