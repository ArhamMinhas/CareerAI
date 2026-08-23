import type { JobDetail } from "@/lib/types/job";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

// docs/SEO.md §2.4 — `JobPosting` is "the single highest-leverage structured data on this
// project" (Google for Jobs eligibility). Every field maps straight from the `jobs`/`companies`
// row that renders the page, never hand-authored, so this can't drift from what's displayed.
export function JobPostingJsonLd({ job }: { job: JobDetail }) {
  const data: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    title: job.title,
    description: job.description,
    datePosted: job.posted_at,
    hiringOrganization: {
      "@type": "Organization",
      name: job.company.name,
      sameAs: `${siteUrl}/companies/${job.company.slug}`,
    },
    employmentType: job.employment_type ?? undefined,
    jobLocationType: job.remote ? "TELECOMMUTE" : undefined,
    jobLocation:
      !job.remote && job.location
        ? {
            "@type": "Place",
            address: { "@type": "PostalAddress", addressLocality: job.location },
          }
        : undefined,
    baseSalary:
      job.salary_min != null || job.salary_max != null
        ? {
            "@type": "MonetaryAmount",
            currency: job.currency ?? "USD",
            value: {
              "@type": "QuantitativeValue",
              minValue: job.salary_min ?? undefined,
              maxValue: job.salary_max ?? undefined,
              unitText: "YEAR",
            },
          }
        : undefined,
  };

  return (
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }} />
  );
}
