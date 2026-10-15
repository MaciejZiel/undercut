import { expect, type APIRequestContext, type APIResponse } from "@playwright/test";
import { BASE_URL } from "./config";

const ALLAUTH = "/api/v1/allauth/browser/v1";

/** Unsafe requests need the CSRF header; the cookie jar of the request context holds the cookie. */
async function csrfHeaders(request: APIRequestContext): Promise<Record<string, string>> {
  const res = await request.get("/api/v1/auth/csrf/");
  expect(res.ok(), "CSRF bootstrap").toBeTruthy();
  const body = (await res.json()) as { csrf_token: string };
  return { "X-CSRFToken": body.csrf_token, Origin: BASE_URL, Referer: `${BASE_URL}/` };
}

export async function apiSend(
  request: APIRequestContext,
  method: "POST" | "PUT" | "PATCH" | "DELETE",
  path: string,
  data?: unknown,
): Promise<APIResponse> {
  return request.fetch(path, { method, data, headers: await csrfHeaders(request) });
}

export type Credentials = { email: string; displayName: string; password: string };

/** Creates the account; allauth signs the new user in on this request context. */
export async function signup(request: APIRequestContext, who: Credentials): Promise<void> {
  const res = await apiSend(request, "POST", `${ALLAUTH}/auth/signup`, {
    email: who.email,
    password: who.password,
    display_name: who.displayName,
  });
  expect(res.status(), `signup: ${await res.text()}`).toBeLessThan(400);
}

/** Consumes a confirmation key (200 when logged in, 401 when only confirmed: both are fine). */
export async function confirmEmailKey(request: APIRequestContext, key: string): Promise<void> {
  const res = await apiSend(request, "POST", `${ALLAUTH}/auth/email/verify`, { key });
  expect([200, 401], `verify: ${await res.text()}`).toContain(res.status());
}

export async function whoAmI(request: APIRequestContext): Promise<{ email_verified?: boolean } | null> {
  const res = await request.get("/api/v1/auth/me/");
  if (!res.ok()) return null;
  const body = (await res.json()) as { authenticated?: boolean; user?: { email_verified?: boolean } | null };
  return body.user ?? null;
}
