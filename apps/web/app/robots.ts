import type { MetadataRoute } from "next";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

/**
 * docs/SEO.md §2.2 — the landing page plus /careers and /skills are indexable as of Phase 6;
 * jobs/companies (Phase 7) and resources (Phase 9) grow this list further as they ship. The
 * authenticated app and /admin are never indexed.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/dashboard", "/admin", "/api"],
    },
    sitemap: `${siteUrl}/sitemap.xml`,
  };
}
