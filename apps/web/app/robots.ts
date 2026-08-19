import type { MetadataRoute } from "next";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

/**
 * docs/SEO.md §2.2 — only the public landing page is indexable today; the rest of this
 * list grows as each route ships (careers/skills in Phase 6, jobs/companies in Phase 7,
 * resources in Phase 9). The authenticated app and /admin are never indexed.
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
