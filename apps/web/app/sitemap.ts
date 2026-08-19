import type { MetadataRoute } from "next";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

/**
 * docs/SEO.md §2.3 — a sitemap index over per-content-type sub-sitemaps is the target
 * shape once /careers, /jobs, /companies, /resources exist. Phase 2 only has the static
 * landing page, so this is the whole sitemap for now.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: siteUrl,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1,
    },
  ];
}
