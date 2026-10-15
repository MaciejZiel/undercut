import { cacheLife, cacheTag } from "next/cache";
import { tags } from "@/lib/api/queries";
import { serverApi, unwrapRequired } from "@/lib/api/server";

/**
 * Everything the dashboard shows comes from one endpoint. Cached for a short time and purged with
 * the same tags as the season and standings pages, so a finished race refreshes it at once.
 */
export async function getDashboard() {
  "use cache";
  cacheLife("minutes");
  cacheTag(tags.standings, tags.seasons, tags.drivers);
  return unwrapRequired(serverApi().GET("/api/v1/dashboard/"));
}
