import createClient from "openapi-fetch";
import type { paths } from "./schema";

export type { paths, components } from "./schema";

/**
 * Server side (RSC, route handlers) talks to Django directly through
 * API_INTERNAL_URL. The browser uses the same origin, where the reverse proxy
 * routes /api to Django, so no CORS and no public backend URL in the bundle.
 */
export function resolveBaseUrl(): string {
  if (typeof window !== "undefined") return "";
  return process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";
}

/**
 * Header the server-side client sends so the backend does not count the Next.js server's own
 * requests (all from one address) against the public anonymous rate limit. The value never
 * reaches the browser: it is read from the server environment only.
 */
export const INTERNAL_TOKEN_HEADER = "x-internal-token";

export function internalHeaders(): Record<string, string> | undefined {
  if (typeof window !== "undefined") return undefined;
  const token = process.env.INTERNAL_API_TOKEN;
  return token ? { [INTERNAL_TOKEN_HEADER]: token } : undefined;
}

export function createApiClient(baseUrl: string = resolveBaseUrl()) {
  return createClient<paths>({ baseUrl, headers: internalHeaders() });
}
