import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ExternalLink, MapPin } from "lucide-react";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { SmoothScroll } from "@/components/layout/smooth-scroll";
import { Section } from "@/components/ui/section";
import { Container } from "@/components/ui/container";
import { ButtonLink } from "@/components/ui/button";
import { Reveal } from "@/components/motion/reveal";
import { BreadcrumbJsonLd } from "@/components/seo/breadcrumb-json-ld";
import { JobPostingJsonLd } from "@/components/seo/job-posting-json-ld";
import { TrackApplicationButton } from "@/components/jobs/track-application-button";
import { fetchPublic, fetchPublicAllPages, PublicApiError } from "@/lib/public-api";
import { cardHoverMotion, cn } from "@/lib/utils";
import type { Job, JobDetail } from "@/lib/types/job";

export const revalidate = 600; // docs/SEO.md §5 — jobs are the highest-churn content

export async function generateStaticParams(): Promise<{ id: string }[]> {
  // Pre-renders every active job at build time; falls back to an empty list if the API isn't
  // reachable during the build (`dynamicParams` defaults to true, so un-prerendered ids still
  // render correctly on first request) — same graceful-degradation precedent as careers/skills.
  try {
    const jobs = await fetchPublicAllPages<Job>("/api/v1/jobs", revalidate);
    return jobs.map((job) => ({ id: job.id }));
  } catch {
    return [];
  }
}

async function getJob(id: string): Promise<JobDetail | null> {
  try {
    return await fetchPublic<JobDetail>(`/api/v1/jobs/${id}`, revalidate);
  } catch (err) {
    if (err instanceof PublicApiError && err.status === 404) return null;
    throw err;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const job = await getJob(id);
  if (!job) return { title: "Job not found" };

  const title = `${job.title} at ${job.company.name}`;
  const description = `${job.title} at ${job.company.name}${job.location ? ` — ${job.location}` : ""}${job.remote ? " (Remote)" : ""}.`;
  return {
    title,
    description,
    openGraph: { title, description, type: "article" },
    twitter: { card: "summary_large_image", title, description },
  };
}

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const job = await getJob(id);
  if (!job) notFound();

  const sortedSkills = [...job.required_skills].sort((a, b) => b.weight - a.weight);

  return (
    <SmoothScroll>
      <JobPostingJsonLd job={job} />
      <BreadcrumbJsonLd
        items={[
          { name: "Jobs", path: "/jobs" },
          { name: job.title, path: `/jobs/${job.id}` },
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
              <div className="mt-4 flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-center">
                <div>
                  <h1 className="max-w-[28ch] text-4xl font-semibold tracking-tighter text-foreground md:text-6xl">
                    {job.title}
                  </h1>
                  <Link
                    href={`/companies/${job.company.slug}`}
                    className="mt-3 inline-block text-lg text-muted-foreground transition-colors hover:text-primary"
                  >
                    {job.company.name}
                  </Link>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {job.apply_url ? (
                    <ButtonLink
                      href={job.apply_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      size="md"
                    >
                      Apply now
                      <ExternalLink className="size-4" strokeWidth={1.75} />
                    </ButtonLink>
                  ) : null}
                  <TrackApplicationButton jobId={job.id} />
                </div>
              </div>
              <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
                {job.location || job.remote ? (
                  <span className="inline-flex items-center gap-1.5">
                    <MapPin className="size-4" strokeWidth={1.75} />
                    {job.remote ? "Remote" : job.location}
                  </span>
                ) : null}
                {job.seniority_level ? <span>{job.seniority_level}</span> : null}
                {job.employment_type ? <span>{job.employment_type}</span> : null}
                {!job.source ? (
                  <span
                    title="This posting is sample content, not a real job listing"
                    className="rounded-full border border-border-strong px-2.5 py-0.5 text-xs text-muted-foreground"
                  >
                    Demo posting
                  </span>
                ) : null}
              </div>
            </Reveal>

            <div className="mt-16 grid grid-cols-1 gap-10 lg:grid-cols-[1fr_22rem]">
              <Reveal delay={0.05}>
                <div className="whitespace-pre-line text-base leading-relaxed text-muted-foreground">
                  {job.description}
                </div>
              </Reveal>

              <Reveal delay={0.1} className="lg:sticky lg:top-28 lg:self-start">
                <div
                  className={cn(
                    cardHoverMotion,
                    "rounded-xl border border-border bg-surface p-6"
                  )}
                >
                  <h2 className="text-sm font-medium text-foreground">Required skills</h2>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Sorted by how heavily each skill counts toward matching against this posting.
                  </p>
                  {sortedSkills.length > 0 ? (
                    <ul className="mt-5 flex flex-col gap-3">
                      {sortedSkills.map(({ skill, weight, is_required }) => (
                        <li key={skill.id} className="flex items-center justify-between gap-3">
                          <Link
                            href={`/skills/${skill.slug}`}
                            className="text-sm text-foreground transition-colors hover:text-primary"
                          >
                            {skill.name}
                          </Link>
                          <span className="flex items-center gap-2">
                            {is_required ? (
                              <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-primary">
                                Required
                              </span>
                            ) : null}
                            <span className="h-1.5 w-12 overflow-hidden rounded-full bg-border">
                              <span
                                className="block h-full rounded-full bg-primary transition-all duration-500"
                                style={{ width: `${weight * 10}%` }}
                              />
                            </span>
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-5 text-sm text-muted-foreground">
                      This posting doesn&apos;t list specific required skills.
                    </p>
                  )}
                </div>
              </Reveal>
            </div>
          </Container>
        </Section>
      </main>
      <Footer />
    </SmoothScroll>
  );
}
