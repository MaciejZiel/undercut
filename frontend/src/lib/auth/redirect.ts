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
