import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockFetch } from "@/test/fetch-mock";
import { HttpError, apiRequest, parseError } from "./http";
import { describeError, formErrors, rateLimitMessage } from "./messages";
import { decodeKey, loginHref, safeNext } from "./redirect";

function clearCookies() {
  for (const c of document.cookie.split(";")) document.cookie = `${c.split("=")[0].trim()}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
}

describe("apiRequest", () => {
  beforeEach(clearCookies);
  afterEach(() => vi.unstubAllGlobals());

  it("sends credentials and no CSRF header on GET", async () => {
    const m = mockFetch({ "GET /api/v1/auth/me/": { body: { is_authenticated: false } } });
    await apiRequest("/api/v1/auth/me/");
    expect(m.calls[0].credentials).toBe("same-origin");
    expect(m.calls[0].headers.get("X-CSRFToken")).toBeNull();
  });

  it("bootstraps the CSRF cookie before an unsafe request and sends it in the header", async () => {
    const m = mockFetch({
      "GET /api/v1/auth/csrf/": () => {
        document.cookie = "csrftoken=tok123; path=/";
        return { body: { csrf_token: "tok123" } };
      },
      "POST /api/v1/leagues/": { status: 201, body: {} },
    });
    await apiRequest("/api/v1/leagues/", { method: "POST", body: { name: "x" } });
    expect(m.calls.map((c) => `${c.method} ${c.url}`)).toEqual(["GET /api/v1/auth/csrf/", "POST /api/v1/leagues/"]);
    expect(m.calls[1].headers.get("X-CSRFToken")).toBe("tok123");
    expect(m.calls[1].credentials).toBe("same-origin");
  });

  it("reuses an existing cookie without a bootstrap call", async () => {
    document.cookie = "csrftoken=abc; path=/";
    const m = mockFetch({ "DELETE /api/v1/leagues/ABC/": { status: 204 } });
    const res = await apiRequest("/api/v1/leagues/ABC/", { method: "DELETE" });
    expect(res.status).toBe(204);
    expect(m.calls).toHaveLength(1);
    expect(m.calls[0].headers.get("X-CSRFToken")).toBe("abc");
  });

  it("throws a network HttpError when fetch rejects", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    await expect(apiRequest("/api/v1/auth/me/")).rejects.toMatchObject({ status: 0, code: "network" });
  });

  it("returns accepted non-2xx statuses instead of throwing", async () => {
    document.cookie = "csrftoken=abc; path=/";
    mockFetch({ "DELETE /x": { status: 401, body: { status: 401 } } });
    await expect(apiRequest("/x", { method: "DELETE", accept: [401] })).resolves.toMatchObject({ status: 401 });
  });
});

describe("error parsing", () => {
  const res = (status: number, body: unknown, headers: Record<string, string> = {}) =>
    new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...headers } });

  it("reads allauth errors with their field", async () => {
    const err = await parseError(res(400, { status: 400, errors: [{ message: "Enter a valid email.", code: "invalid", param: "email" }] }));
    expect(err.fields.email).toEqual(["Enter a valid email."]);
    expect(formErrors(err, ["email", "password"])).toEqual({ form: null, fields: { email: "Enter a valid email." } });
  });

  it("reads {detail, code}", async () => {
    const err = await parseError(res(403, { detail: "closed", code: "predictions_locked" }));
    expect(err.code).toBe("predictions_locked");
    expect(describeError(err)).toBe("Predictions for this round are closed.");
  });

  it("reads DRF field errors", async () => {
    const err = await parseError(res(400, { name: ["This field is required."] }));
    expect(err.fields.name).toEqual(["This field is required."]);
  });

  it("maps 429 to the rate-limit message, using Retry-After when given", async () => {
    const err = await parseError(res(429, { status: 429 }, { "Retry-After": "900" }));
    expect(err).toBeInstanceOf(HttpError);
    expect(describeError(err)).toBe(rateLimitMessage(900));
    expect(describeError(err)).toContain("15 minutes");
    expect(rateLimitMessage(null)).toContain("Too many attempts");
  });

  it("never shows raw server errors for 5xx", () => {
    expect(describeError(new HttpError(500, { messages: ["Traceback..."] }))).toBe("The server had a problem. Try again in a moment.");
  });
});

describe("redirect helpers", () => {
  it("only accepts same-origin paths", () => {
    expect(safeNext("/predict/2026/3")).toBe("/predict/2026/3");
    expect(safeNext("//evil.com")).toBeNull();
    expect(safeNext("https://evil.com")).toBeNull();
    expect(safeNext("/\\evil.com")).toBeNull();
    expect(safeNext(null)).toBeNull();
  });
  it("keeps the target in the login link", () => {
    expect(loginHref("/predict/2026/3?x=1")).toBe("/login?next=%2Fpredict%2F2026%2F3%3Fx%3D1");
    expect(loginHref("//evil.com")).toBe("/login");
  });
});

describe("decodeKey", () => {
  it("decodes the percent-encoded key Next passes to a page", () => {
    expect(decodeKey("MQ%3A1abc-_xyz")).toBe("MQ:1abc-_xyz");
  });

  it("leaves a plain key and a malformed one untouched", () => {
    expect(decodeKey("MQ:1abc")).toBe("MQ:1abc");
    expect(decodeKey("100%")).toBe("100%");
  });

  it("round-trips through the alias redirect without double encoding", () => {
    const fromMail = "MQ:1abc";
    const params = encodeURIComponent(fromMail); // what Next gives the alias page
    expect(encodeURIComponent(decodeKey(params))).toBe("MQ%3A1abc");
    expect(decodeKey(decodeKey(params))).toBe(fromMail);
  });
});
