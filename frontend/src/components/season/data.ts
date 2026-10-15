import { cacheLife, cacheTag } from "next/cache";
import { tags } from "@/lib/api/queries";
import { serverApi, unwrap } from "@/lib/api/server";

/** Drivers x rounds grid of one season. Null when the season does not exist. */
export async function getSeasonMatrix(year: number) {
  "use cache";
  cacheLife("hours");
  cacheTag(tags.seasons, tags.season(year));
  return unwrap(serverApi().GET("/api/v1/seasons/{year}/matrix/", { params: { path: { year } } }));
}
