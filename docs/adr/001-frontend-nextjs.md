# ADR 001: Next.js for the frontend

Status: accepted

## Context
Undercut is a public site: pages must be fast on the first visit, indexable, and carry
per-page metadata and share images. Part of it is highly interactive (charts, replay).

## Decision
Next.js (App Router) with TypeScript. Catalog pages are server-rendered and tag-cached;
analytics, replay, predictions and account screens are client components fed by TanStack Query.
ECharts (canvas) draws the large series. API types are generated from the backend's OpenAPI
schema (`openapi-typescript`), so the contract cannot drift silently.

## Consequences
- A Node process runs next to Django in production.
- Cache invalidation must be explicit: see ADR 003 and the `webcache` module.
- Per-user data must never enter the server cache.
