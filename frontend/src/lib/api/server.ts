import { createApiClient } from "./client";

export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message?: string) {
    super(message ?? `API request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
  }
}

type Result<T> = { data?: T; error?: unknown; response: Response };

/**
 * Unwrap an openapi-fetch result: the body on success, null for 404 (the page
 * then calls notFound()), an ApiError for anything else so the error boundary
 * shows the retry state. Errors are thrown, which keeps them out of the cache.
 */
export async function unwrap<T>(call: Promise<Result<T>>): Promise<T | null> {
  let result: Result<T>;
  try {
    result = await call;
  } catch (cause) {
    throw new ApiError(0, `API unreachable: ${cause instanceof Error ? cause.message : String(cause)}`);
  }
  if (result.response.status === 404) return null;
  if (!result.response.ok || result.data === undefined) throw new ApiError(result.response.status);
  return result.data;
}

/** Same as unwrap, but a missing resource is also an error (lists, search). */
export async function unwrapRequired<T>(call: Promise<Result<T>>): Promise<T> {
  const data = await unwrap(call);
  if (data === null) throw new ApiError(404);
  return data;
}

export const serverApi = () => createApiClient();
