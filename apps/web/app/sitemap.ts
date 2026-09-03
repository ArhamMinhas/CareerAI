import type { MetadataRoute } from "next";
import { fetchPublic, fetchPublicAllPages } from "@/lib/public-api";
import type { CareerPath } from "@/lib/types/career-path";
import type { Skill } from "@/lib/types/profile";
import type { Job } from "@/lib/types/job";
import type { Resource } from "@/lib/types/resource";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

// docs/SEO.md §2.3 documents a sitemap index over per-content-type sub-sitemaps, with jobs
// getting their own *paginated* sub-sitemap (`sitemap/jobs/0.xml`, ...) since that's the
// largest, fastest-changing content type. At this phase's actual data volume (a seed script's
// worth of jobs/companies, not a real ingested catalog) that infrastructure is premature — a
// single flat sitemap covers everything fine, same documented scope deviation as Phase 6's
// careers/skills sitemap. Revisit once real job-ingestion volume justifies the split.
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [careerPaths, curatedSkills, jobs, resources] = await Promise.all([
    fetchPublic<CareerPath[]>("/api/v1/careers", 3600).catch(() => []),
    fetchPublic<Skill[]>("/api/v1/skills/curated", 3600).catch(() => []),
    fetchPublicAllPages<Job>("/api/v1/jobs", 600).catch(() => []),
    fetchPublic<Resource[]>("/api/v1/resources", 3600).catch(() => []),
  ]);

  const companySlugs = Array.from(new Set(jobs.map((job) => job.company.slug)));

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
    {
      url: `${siteUrl}/jobs`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 0.8,
    },
    {
      url: `${siteUrl}/resources`,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 0.8,
    },
    // `lastModified` is each row's real `updated_at` (docs/SEO.md's "sourced from each row's
    // updated_at" requirement) — not the hardcoded `new Date()` this sitemap used for careers
    // before Phase 9 added `updated_at` to `CareerPathRead` specifically to fix this.
    ...careerPaths.map((careerPath) => ({
      url: `${siteUrl}/careers/${careerPath.slug}`,
      lastModified: new Date(careerPath.updated_at),
      changeFrequency: "monthly" as const,
      priority: 0.7,
    })),
    ...resources.map((resource) => ({
      url: `${siteUrl}/resources/${resource.slug}`,
      lastModified: new Date(resource.updated_at),
      changeFrequency: "monthly" as const,
      priority: 0.7,
    })),
    ...curatedSkills.map((skill) => ({
      url: `${siteUrl}/skills/${skill.slug}`,
      lastModified: new Date(),
      changeFrequency: "monthly" as const,
      priority: 0.6,
    })),
    ...jobs.map((job) => ({
      url: `${siteUrl}/jobs/${job.id}`,
      lastModified: new Date(),
      changeFrequency: "weekly" as const,
      priority: 0.7,
    })),
    ...companySlugs.map((slug) => ({
      url: `${siteUrl}/companies/${slug}`,
      lastModified: new Date(),
      changeFrequency: "monthly" as const,
      priority: 0.6,
    })),
  ];
}
