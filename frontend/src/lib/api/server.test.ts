import { describe, expect, it } from "vitest";
import { ApiError, unwrap, unwrapRequired } from "./server";

const ok = <T,>(data: T, status = 200) => Promise.resolve({ data, response: new Response(null, { status }) });
const fail = (status: number) => Promise.resolve({ error: {}, response: new Response(null, { status }) });

describe("unwrap", () => {
  it("returns the body on success", async () => {
    expect(await unwrap(ok({ a: 1 }))).toEqual({ a: 1 });
  });

  it("returns null for 404 so pages can call notFound()", async () => {
    expect(await unwrap(fail(404))).toBeNull();
  });

  it("throws ApiError for server errors so they are never cached", async () => {
    await expect(unwrap(fail(500))).rejects.toMatchObject({ name: "ApiError", status: 500 });
    await expect(unwrap(fail(400))).rejects.toBeInstanceOf(ApiError);
  });

  it("turns a network failure into an ApiError", async () => {
    await expect(unwrap(Promise.reject(new TypeError("fetch failed")))).rejects.toMatchObject({ status: 0 });
  });

  it("unwrapRequired treats 404 as an error", async () => {
    await expect(unwrapRequired(fail(404))).rejects.toMatchObject({ status: 404 });
  });
});
