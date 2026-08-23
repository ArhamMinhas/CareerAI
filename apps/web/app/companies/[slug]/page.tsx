import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { SmoothScroll } from "@/components/layout/smooth-scroll";
import { Section } from "@/components/ui/section";
import { Container } from "@/components/ui/container";
import { Reveal } from "@/components/motion/reveal";
import { BreadcrumbJsonLd } from "@/components/seo/breadcrumb-json-ld";
import { OrganizationJsonLd } from "@/components/seo/organization-json-ld";
import { JobCard } from "@/components/jobs/job-card";
import { fetchPublic, fetchPublicAllPages, PublicApiError } from "@/lib/public-api";
import type { Company, CompanyDetail } from "@/lib/types/job";

// Companies churn far less than job postings (docs/SEO.md §5), so this uses the same
// hours-long ISR interval as careers/skills rather than the jobs listing's short one.
export const revalidate = 3600;

export async function generateStaticParams(): Promise<{ slug: string }[]> {
  try {
    // There's no `/companies` list endpoint (docs/API.md §5 only documents `{slug}` and
    // `{slug}/jobs`) — every company that has at least one active job is discoverable by
    // walking the jobs listing instead, deduped by slug.
    const jobs = await fetchPublicAllPages<{ company: Company }>("/api/v1/jobs", revalidate);
    const slugs = new Set(jobs.map((job) => job.company.slug));
    return Array.from(slugs).map((slug) => ({ slug }));
  } catch {
    return [];
  }
}

async function getCompany(slug: string): Promise<CompanyDetail | null> {
  try {
    return await fetchPublic<CompanyDetail>(`/api/v1/companies/${slug}`, revalidate);
  } catch (err) {
    if (err instanceof PublicApiError && err.status === 404) return null;
    throw err;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const company = await getCompany(slug);
  if (!company) return { title: "Company not found" };

  const title = company.name;
  const description = company.description ?? `Open roles at ${company.name}.`;
  return {
    title,
    description,
    openGraph: { title, description, type: "website" },
    twitter: { card: "summary_large_image", title, description },
  };
}

export default async function CompanyDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const company = await getCompany(slug);
  if (!company) notFound();

  return (
    <SmoothScroll>
      <OrganizationJsonLd
        name={company.name}
        slug={company.slug}
        description={company.description}
        logoUrl={company.logo_url}
      />
      <BreadcrumbJsonLd
        items={[
          { name: "Jobs", path: "/jobs" },
          { name: company.name, path: `/companies/${company.slug}` },
        ]}
      />
      <Navbar />
      <main>
        <Section className="pb-16 pt-24 lg:pt-28">
          <Container>
            <Reveal>
              <Link
                href="/jobs"
                className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
              >
                ← All jobs
              </Link>
              {company.industry ? (
                <p className="mt-4 text-sm font-medium text-primary">{company.industry}</p>
              ) : null}
              <h1 className="mt-3 max-w-[24ch] text-4xl font-semibold tracking-tighter text-foreground md:text-6xl">
                {company.name}
              </h1>
              {company.description ? (
                <p className="mt-5 max-w-[65ch] text-lg leading-relaxed text-muted-foreground">
                  {company.description}
                </p>
              ) : null}
            </Reveal>

            <div className="mt-16">
              <Reveal>
                <h2 className="text-2xl font-semibold tracking-tight text-foreground">
                  Open roles{company.jobs.length > 0 ? ` (${company.jobs.length})` : ""}
                </h2>
              </Reveal>
              {company.jobs.length > 0 ? (
                <div className="mt-8 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
                  {company.jobs.map((job, index) => (
                    <JobCard key={job.id} job={job} delay={Math.min(index * 0.05, 0.3)} />
                  ))}
                </div>
              ) : (
                <p className="mt-6 text-sm text-muted-foreground">
                  No open roles at {company.name} right now.
                </p>
              )}
            </div>
          </Container>
        </Section>
      </main>
      <Footer />
    </SmoothScroll>
  );
}
