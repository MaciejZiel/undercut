import type { Metadata } from "next";

export const SITE_NAME = "Undercut";
export const DEFAULT_SITE_URL = "https://undercut.maciejzielinski.dev";
export const SITE_DESCRIPTION = "Formula 1 stats, race analytics and predictions. Unofficial fan site.";

/** Public origin without a trailing slash. Override with NEXT_PUBLIC_SITE_URL. */
export function siteUrl(): string {
  const raw = process.env.NEXT_PUBLIC_SITE_URL?.trim();
  return (raw ? raw : DEFAULT_SITE_URL).replace(/\/+$/, "");
}

export function absoluteUrl(path: string): string {
  return `${siteUrl()}${path.startsWith("/") ? path : `/${path}`}`;
}

/**
 * Title, description, canonical and Open Graph for one page. `title` is the
 * short page title (the layout template adds the site name); Open Graph does
 * not use the template, so the full title is built here. Images come from the
 * opengraph-image file convention.
 */
export function pageMetadata({
  title,
  description,
  path,
}: {
  title: string;
  description: string;
  path: string;
}): Metadata {
  return {
    title,
    description,
    alternates: { canonical: path },
    openGraph: {
      title: `${title} | ${SITE_NAME}`,
      description,
      url: path,
      siteName: SITE_NAME,
      type: "website",
      locale: "en_GB",
    },
  };
}
