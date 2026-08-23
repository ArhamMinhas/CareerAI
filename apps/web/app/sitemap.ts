import type { MetadataRoute } from "next";
import { fetchPublic } from "@/lib/public-api";
import type { CareerPath } from "@/lib/types/career-path";
import type { Skill } from "@/lib/types/profile";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

// docs/SEO.md §2.3 — a sitemap index over per-content-type sub-sitemaps is the target shape
// once /jobs also exists (jobs get their own paginated sub-sitemap since that's the largest,
// fastest-changing content type). Careers and skills are small curated catalogs, so a single
// flat sitemap covers them fine for now — revisit when /jobs lands in Phase 7.
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [careerPaths, curatedSkills] = await Promise.all([
    fetchPublic<CareerPath[]>("/api/v1/careers", 3600).catch(() => []),
    fetchPublic<Skill[]>("/api/v1/skills/curated", 3600).catch(() => []),
  ]);

  return [
    {
      url: siteUrl,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${siteUrl}/careers`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.8,
    },
    ...careerPaths.map((careerPath) => ({
      url: `${siteUrl}/careers/${careerPath.slug}`,
      lastModified: new Date(),
      changeFrequency: "monthly" as const,
      priority: 0.7,
    })),
    ...curatedSkills.map((skill) => ({
      url: `${siteUrl}/skills/${skill.slug}`,
      lastModified: new Date(),
      changeFrequency: "monthly" as const,
      priority: 0.6,
    })),
  ];
}
