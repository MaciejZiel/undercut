import createClient from "openapi-fetch";

/**
 * Hand-written minimal `paths` type covering GET /api/health/ only.
 * It is a stand-in until the OpenAPI schema is generated with
 * `npm run gen:api` (src/lib/api/schema.d.ts); then import `paths` from there.
 */
export interface paths {
  "/api/health/": {
    get: {
      parameters: { query?: never; header?: never; path?: never; cookie?: never };
      requestBody?: never;
      responses: {
        200: {
          headers: Record<string, unknown>;
          content: { "application/json": { status: string } };
        };
      };
    };
  };
}

/**
 * Server side (RSC, route handlers) talks to Django directly through
 * API_INTERNAL_URL. The browser uses the same origin, where the reverse proxy
 * routes /api to Django, so no CORS and no public backend URL in the bundle.
 */
export function resolveBaseUrl(): string {
  if (typeof window !== "undefined") return "";
  return process.env.API_INTERNAL_URL ?? "http://localhost:8000";
}

export function createApiClient(baseUrl: string = resolveBaseUrl()) {
  return createClient<paths>({ baseUrl });
}

export const api = createApiClient();
