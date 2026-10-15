import { cacheLife, cacheTag } from "next/cache";
import { tags } from "@/lib/api/queries";
import { serverApi, unwrap } from "@/lib/api/server";

/** Mathematical title race of a season (default: the latest with standings). Null for an unknown season. */
export async function getTitleRace(season?: number) {
  "use cache";
  cacheLife("hours");
  cacheTag(tags.standings, ...(season ? [tags.season(season)] : []));
  return unwrap(serverApi().GET("/api/v1/standings/title-race/", { params: { query: { season } } }));
}
