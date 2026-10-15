import { cacheLife, cacheTag } from "next/cache";
import { tags } from "@/lib/api/queries";
import { serverApi, unwrap } from "@/lib/api/server";

/** Season calendar with sessions. Null when the requested year does not exist. */
export async function getCalendar(year?: number) {
  "use cache";
  cacheLife("minutes");
  cacheTag(tags.seasons, ...(year ? [tags.season(year)] : []));
  return unwrap(serverApi().GET("/api/v1/calendar/", { params: { query: { year } } }));
}
