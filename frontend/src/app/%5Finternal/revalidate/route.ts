import { timingSafeEqual } from "node:crypto";
import { revalidateTag } from "next/cache";

/**
 * POST /_internal/revalidate
 *
 * Called by the backend ("web cache" event handler) to purge cache tags.
 * The /api prefix belongs to Django behind the proxy, hence this path.
 * Header `x-revalidate-secret` must equal REVALIDATE_SECRET; body: {"tags": ["driver:max-verstappen"]}.
 * The proxy should not expose /_internal to the public internet.
 */

const MAX_TAGS = 100;
// Same grammar as the tags in lib/api/queries.ts: "drivers", "round:2024-5", "season:2024".
const TAG_PATTERN = /^[a-z][a-z-]*(:[A-Za-z0-9._-]{1,200})?$/;

function secretsMatch(given: string | null, expected: string): boolean {
  if (given === null) return false;
  const a = Buffer.from(given);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

export async function POST(request: Request): Promise<Response> {
  const expected = process.env.REVALIDATE_SECRET;
  if (!expected) {
    // Fail closed: without a configured secret nobody may purge the cache.
    return Response.json({ error: "Revalidation is not configured" }, { status: 503 });
  }
  if (!secretsMatch(request.headers.get("x-revalidate-secret"), expected)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Body must be JSON" }, { status: 400 });
  }
  const tags = (body as { tags?: unknown } | null)?.tags;
  if (
    !Array.isArray(tags) ||
    tags.length === 0 ||
    tags.length > MAX_TAGS ||
    !tags.every((t): t is string => typeof t === "string" && TAG_PATTERN.test(t))
  ) {
    return Response.json(
      { error: `"tags" must be a non-empty array of at most ${MAX_TAGS} valid tag strings` },
      { status: 400 },
    );
  }

  const unique = [...new Set(tags)];
  // expire: 0 because the caller is a webhook: stale pages must not be served after a results change.
  for (const tag of unique) revalidateTag(tag, { expire: 0 });
  return Response.json({ revalidated: unique });
}
