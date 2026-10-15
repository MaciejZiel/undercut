/**
 * Content-Security-Policy for the Next.js pages (NFR-201).
 *
 * `script-src` keeps 'unsafe-inline': Next streams inline bootstrap scripts, and a per-request nonce
 * would force every page to be rendered dynamically, which defeats the cached, partially prerendered
 * pages. Everything else is locked to this origin, so injected markup cannot load code from
 * elsewhere, embed the site, submit forms elsewhere or send data to another host.
 */
export function contentSecurityPolicy(isDev = false): string {
  const directives: Record<string, string[]> = {
    "default-src": ["'self'"],
    "script-src": ["'self'", "'unsafe-inline'", ...(isDev ? ["'unsafe-eval'"] : [])],
    "style-src": ["'self'", "'unsafe-inline'"],
    "img-src": ["'self'", "data:", "blob:"],
    "font-src": ["'self'", "data:"],
    "connect-src": ["'self'"],
    // The circuit page embeds an OpenStreetMap map (FR-104); no other site may be framed.
    "frame-src": ["https://www.openstreetmap.org"],
    "worker-src": ["'self'", "blob:"],
    "manifest-src": ["'self'"],
    "object-src": ["'none'"],
    "base-uri": ["'self'"],
    "form-action": ["'self'"],
    "frame-ancestors": ["'none'"],
  };
  return Object.entries(directives)
    .map(([name, sources]) => `${name} ${sources.join(" ")}`)
    .join("; ");
}
