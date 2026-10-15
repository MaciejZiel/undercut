import type { MetadataRoute } from "next";
import { getCircuits, getConstructors, getDrivers, getSeason, getSeasons } from "@/lib/api/queries";
import { circuitHref, constructorHref, driverHref, roundHref, seasonHref } from "@/lib/routes";
import { absoluteUrl } from "@/lib/seo";

const STATIC_PATHS = [
  "/",
  "/calendar",
  "/standings/drivers",
  "/standings/constructors",
  "/compare",
  "/catalog",
  "/drivers",
  "/constructors",
  "/circuits",
  "/seasons",
  "/about",
  "/privacy",
] as const;

const MAX_PAGES = 30; // guard: 100 rows per page, so 3000 rows per list
const SEASON_BATCH = 8;

type Page<T> = { results: T[]; next?: string | null } | null;

async function allPages<T>(fetchPage: (page: number) => Promise<Page<T>>): Promise<T[]> {
  const rows: T[] = [];
  for (let page = 1; page <= MAX_PAGES; page++) {
    const data = await fetchPage(page);
    if (!data) break;
    rows.push(...data.results);
    if (!data.next) break;
  }
  return rows;
}

/** Catalog URLs from the API. Any failure (API down at build time) throws and the caller falls back to static routes. */
async function catalogPaths(): Promise<string[]> {
  const [drivers, teams, circuits, seasons] = await Promise.all([
    allPages((page) => getDrivers({ page, page_size: 100, constructor: undefined })),
    allPages((page) => getConstructors({ page, page_size: 100 })),
    allPages((page) => getCircuits({ page, page_size: 100 })),
    allPages((page) => getSeasons(page)),
  ]);
  const paths = [
    ...drivers.map((d) => driverHref(d.slug)),
    ...teams.map((t) => constructorHref(t.slug)),
    ...circuits.map((c) => circuitHref(c.slug)),
    ...seasons.map((s) => seasonHref(s.year)),
  ];
  const years = seasons.map((s) => s.year);
  for (let i = 0; i < years.length; i += SEASON_BATCH) {
    const details = await Promise.all(years.slice(i, i + SEASON_BATCH).map((y) => getSeason(y)));
    for (const season of details) {
      for (const r of season?.rounds ?? []) {
        if (r.round != null && !r.is_cancelled) paths.push(roundHref(season!.year, r.round));
      }
    }
  }
  return paths;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const statics: MetadataRoute.Sitemap = STATIC_PATHS.map((p) => ({
    url: absoluteUrl(p),
    changeFrequency: p === "/" || p === "/calendar" ? "daily" : "weekly",
    priority: p === "/" ? 1 : 0.7,
  }));
  let dynamic: string[] = [];
  try {
    dynamic = await catalogPaths();
  } catch {
    return statics;
  }
  return [...statics, ...dynamic.map((p) => ({ url: absoluteUrl(p), changeFrequency: "weekly" as const, priority: 0.5 }))];
}
