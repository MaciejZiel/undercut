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

export function createApiClient(baseUrl: string = resolveBaseUrl()) {
  return createClient<paths>({ baseUrl });
}
