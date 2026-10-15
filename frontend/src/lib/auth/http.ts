/**
 * Browser-side HTTP helper for everything that depends on the visitor's session.
 *
 * - Always `credentials: "same-origin"` (the reverse proxy serves /api on the same origin).
 * - Unsafe methods carry the CSRF token from the `csrftoken` cookie in `X-CSRFToken`; when the
 *   cookie is missing it is bootstrapped through GET /api/v1/auth/csrf/ first.
 * - Failures are normalised into HttpError, whatever the backend shape was (allauth headless
 *   `errors[]`, `{detail, code}` or DRF field errors).
 */

export const CSRF_COOKIE = "csrftoken";
export const CSRF_HEADER = "X-CSRFToken";
export const CSRF_ENDPOINT = "/api/v1/auth/csrf/";

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

export class HttpError extends Error {
  readonly status: number;
  readonly code: string | null;
  /** Human readable messages, one per problem. */
  readonly messages: string[];
  /** Messages by form field, when the backend named the field. */
  readonly fields: Record<string, string[]>;
  /** Seconds from the Retry-After header, when present (429). */
  readonly retryAfter: number | null;

  constructor(
    status: number,
    init: { code?: string | null; messages?: string[]; fields?: Record<string, string[]>; retryAfter?: number | null } = {},
  ) {
    const messages = init.messages ?? [];
    super(messages[0] ?? `Request failed with status ${status}`);
    this.name = "HttpError";
    this.status = status;
    this.code = init.code ?? null;
    this.messages = messages;
    this.fields = init.fields ?? {};
    this.retryAfter = init.retryAfter ?? null;
  }
}

export function isHttpError(e: unknown): e is HttpError {
  return e instanceof HttpError;
}

export function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  for (const part of document.cookie.split(";")) {
    const [k, ...rest] = part.trim().split("=");
    if (k === name) return decodeURIComponent(rest.join("="));
  }
  return null;
}

let csrfInFlight: Promise<string> | null = null;

/** Returns the CSRF token, fetching the cookie from the backend when it is not there yet. */
export async function ensureCsrfToken(force = false): Promise<string> {
  if (!force) {
    const existing = readCookie(CSRF_COOKIE);
    if (existing) return existing;
  }
  csrfInFlight ??= (async () => {
    try {
      const res = await fetch(CSRF_ENDPOINT, { credentials: "same-origin", headers: { Accept: "application/json" } });
      if (!res.ok) throw new HttpError(res.status, { messages: ["Could not start a secure session. Reload the page."] });
      const body = (await res.json().catch(() => null)) as { csrf_token?: string } | null;
      return readCookie(CSRF_COOKIE) ?? body?.csrf_token ?? "";
    } finally {
      csrfInFlight = null;
    }
  })();
  return csrfInFlight;
}

type Json = unknown;

export type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: Json;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  /** Statuses that are returned instead of thrown (for example allauth answers 401 after logout). */
  accept?: number[];
};

export type ApiResult<T> = { data: T; status: number; response: Response };

export async function parseError(res: Response): Promise<HttpError> {
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  const retry = Number(res.headers.get("Retry-After"));
  const retryAfter = Number.isFinite(retry) && retry > 0 ? retry : null;
  const messages: string[] = [];
  const fields: Record<string, string[]> = {};
  let code: string | null = null;
  const add = (msg: unknown, field?: string) => {
    if (typeof msg !== "string" || !msg) return;
    messages.push(msg);
    if (field) (fields[field] ??= []).push(msg);
  };

  if (body && typeof body === "object") {
    const b = body as Record<string, unknown>;
    if (Array.isArray(b.errors)) {
      // allauth headless: {status, errors: [{message, code, param?}]}
      for (const e of b.errors as Array<Record<string, unknown>>) {
        add(e.message, typeof e.param === "string" ? e.param : undefined);
        if (!code && typeof e.code === "string") code = e.code;
      }
    } else if (typeof b.detail === "string") {
      // {detail, code}: project errors and DRF generic errors
      add(b.detail);
      if (typeof b.code === "string") code = b.code;
    } else {
      // DRF validation errors: {field: ["msg"]} (non_field_errors has no field)
      for (const [field, value] of Object.entries(b)) {
        const list = Array.isArray(value) ? value : [value];
        for (const m of list) add(m, field === "non_field_errors" ? undefined : field);
      }
    }
  } else if (Array.isArray(body)) {
    for (const m of body) add(m);
  }
  return new HttpError(res.status, { code, messages, fields, retryAfter });
}

export async function apiRequest<T = unknown>(path: string, opts: RequestOptions = {}): Promise<ApiResult<T>> {
  const method = opts.method ?? "GET";
  const unsafe = !SAFE_METHODS.has(method);

  const send = async (forceCsrf: boolean): Promise<Response> => {
    const headers: Record<string, string> = { Accept: "application/json", ...opts.headers };
    let body: string | undefined;
    if (opts.body !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(opts.body);
    }
    if (unsafe) headers[CSRF_HEADER] = await ensureCsrfToken(forceCsrf);
    try {
      return await fetch(path, { method, headers, body, credentials: "same-origin", signal: opts.signal });
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
      throw new HttpError(0, { code: "network", messages: ["Could not reach the server. Check your connection and try again."] });
    }
  };

  let res = await send(false);
  if (unsafe && res.status === 403) {
    // A stale CSRF cookie (for example after login rotated it): refresh once and retry.
    const probe = await res.clone().text().catch(() => "");
    if (/csrf/i.test(probe)) res = await send(true);
  }

  if (!res.ok && !opts.accept?.includes(res.status)) throw await parseError(res);

  let data: unknown = null;
  if (res.status !== 204) {
    const text = await res.text().catch(() => "");
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = text;
      }
    }
  }
  return { data: data as T, status: res.status, response: res };
}

export async function apiJson<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
  return (await apiRequest<T>(path, opts)).data;
}

/** TanStack Query `retry` that never repeats 4xx answers (they will not change) and tries 5xx once. */
export function retryServerErrorsOnce(failureCount: number, error: unknown): boolean {
  if (isHttpError(error) && error.status >= 400 && error.status < 500) return false;
  return failureCount < 1;
}
