/** Only same-origin absolute paths may be used as a post-login target (no open redirect). */
export function safeNext(value: string | null | undefined): string | null {
  if (!value) return null;
  if (!value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return null;
  if (/[\r\n]/.test(value)) return null;
  return value;
}

export function loginHref(next?: string | null): string {
  const target = safeNext(next);
  return target ? `/login?next=${encodeURIComponent(target)}` : "/login";
}

export function registerHref(next?: string | null): string {
  const target = safeNext(next);
  return target ? `/register?next=${encodeURIComponent(target)}` : "/register";
}

/**
 * Next hands dynamic route params over still percent-encoded ("MQ%3Axyz"). Keys from e-mail links
 * must reach the API as the plain string the mail contained, so decode exactly once here.
 */
export function decodeKey(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}
