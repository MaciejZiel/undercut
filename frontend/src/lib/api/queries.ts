import { cacheLife, cacheTag } from "next/cache";
import type { components, paths } from "./client";
import { serverApi, unwrap, unwrapRequired } from "./server";

/**
 * Server-side data access for the catalog pages. Every function is cached with
 * `use cache` and tagged, so a revalidation call to /_internal/revalidate can
 * purge exactly what changed. Tags: `drivers`, `driver:<slug>`, `constructors`,
 * `constructor:<slug>`, `circuits`, `circuit:<slug>`, `seasons`, `season:<year>`,
 * `round:<year>-<round>` and `search`. See `tags` below for the builders.
 *
 * Detail functions return null for a 404 so pages can call notFound(); list
 * functions return null for a page past the end; other failures throw (and are
 * therefore never cached).
 */

export const tags = {
  drivers: "drivers",
  driver: (slug: string) => `driver:${slug}`,
  constructors: "constructors",
  constructor: (slug: string) => `constructor:${slug}`,
  circuits: "circuits",
  circuit: (slug: string) => `circuit:${slug}`,
  seasons: "seasons",
  season: (year: number) => `season:${year}`,
  round: (year: number, round: number) => `round:${year}-${round}`,
  search: "search",
} as const;

type Schemas = components["schemas"];
type Query<P extends keyof paths> = paths[P] extends { get: { parameters: { query?: infer Q } } } ? Q : never;

export type DriverQuery = NonNullable<Query<"/api/v1/drivers/">>;
export type ConstructorQuery = NonNullable<Query<"/api/v1/constructors/">>;
export type CircuitQuery = NonNullable<Query<"/api/v1/circuits/">>;
export type SessionType = "RACE" | "SPRINT" | "Q";
export type RaceResults = Schemas["RaceSessionResults"];
export type QualifyingResults = Schemas["QualifyingSessionResults"];

export async function getDrivers(query: DriverQuery) {
  "use cache";
  cacheLife("hours");
  cacheTag(tags.drivers);
  return unwrap(serverApi().GET("/api/v1/drivers/", { params: { query } }));
}

export async function getDriver(slug: string) {
  "use cache";
  cacheLife("hours");
  cacheTag(tags.drivers, tags.driver(slug));
  return unwrap(serverApi().GET("/api/v1/drivers/{slug}/", { params: { path: { slug } } }));
}

export async function getConstructors(query: ConstructorQuery) {
  "use cache";
  cacheLife("hours");
  cacheTag(tags.constructors);
  return unwrap(serverApi().GET("/api/v1/constructors/", { params: { query } }));
}

export async function getConstructor(slug: string) {
  "use cache";
  cacheLife("hours");
  cacheTag(tags.constructors, tags.constructor(slug));
  return unwrap(serverApi().GET("/api/v1/constructors/{slug}/", { params: { path: { slug } } }));
}

export async function getCircuits(query: CircuitQuery) {
  "use cache";
  cacheLife("hours");
  cacheTag(tags.circuits);
  return unwrap(serverApi().GET("/api/v1/circuits/", { params: { query } }));
}

export async function getCircuit(slug: string) {
  "use cache";
  cacheLife("hours");
  cacheTag(tags.circuits, tags.circuit(slug));
  return unwrap(serverApi().GET("/api/v1/circuits/{slug}/", { params: { path: { slug } } }));
}

export async function getSeasons(page: number) {
  "use cache";
  cacheLife("hours");
  cacheTag(tags.seasons);
  return unwrap(serverApi().GET("/api/v1/seasons/", { params: { query: { page, page_size: 100 } } }));
}

export async function getSeason(year: number) {
  "use cache";
  cacheLife("hours");
  cacheTag(tags.seasons, tags.season(year));
  return unwrap(serverApi().GET("/api/v1/seasons/{year}/", { params: { path: { year } } }));
}

export async function getRound(year: number, round: number) {
  "use cache";
  cacheLife("hours");
  cacheTag(tags.season(year), tags.round(year, round));
  return unwrap(serverApi().GET("/api/v1/rounds/{year}/{round}/", { params: { path: { year, round } } }));
}

/** Returns null when the round or that session does not exist. */
export async function getRoundResults(year: number, round: number, session: SessionType) {
  "use cache";
  cacheLife("hours");
  cacheTag(tags.season(year), tags.round(year, round));
  return unwrap(
    serverApi().GET("/api/v1/rounds/{year}/{round}/results/", {
      params: { path: { year, round }, query: { session } },
    }),
  );
}

/** Full results page for /search. Header suggestions call the same endpoint from the browser. */
export async function searchCatalog(q: string) {
  "use cache";
  cacheLife("minutes");
  cacheTag(tags.search);
  return unwrapRequired(serverApi().GET("/api/v1/search/", { params: { query: { q } } }));
}
