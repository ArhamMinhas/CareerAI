import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { SmoothScroll } from "@/components/layout/smooth-scroll";
import { Section } from "@/components/ui/section";
import { Container } from "@/components/ui/container";
import { Reveal } from "@/components/motion/reveal";
import { CareerCard } from "@/components/careers/career-card";
import { BreadcrumbJsonLd } from "@/components/seo/breadcrumb-json-ld";
import { fetchPublic, PublicApiError } from "@/lib/public-api";
import { cn } from "@/lib/utils";
import type { CareerPath, CareerPathDetail } from "@/lib/types/career-path";

export const revalidate = 3600;

export async function generateStaticParams(): Promise<{ slug: string }[]> {
  // Pre-renders every career path at build time (docs/SEO.md §5's "SSG + ISR" — the catalog
  // is small and curated, so there's no reason to defer this to first-request SSR). Falls back
  // to an empty list if the API isn't reachable during the build (e.g. CI's frontend-only job
  // never runs a backend) — `dynamicParams` defaults to true, so un-prerendered slugs still
  // render correctly on first request instead of failing the whole build.
  try {
    const careerPaths = await fetchPublic<CareerPath[]>("/api/v1/careers", revalidate);
    return careerPaths.map((careerPath) => ({ slug: careerPath.slug }));
  } catch {
    return [];
  }
}

async function getCareerPath(slug: string): Promise<CareerPathDetail | null> {
  try {
    return await fetchPublic<CareerPathDetail>(`/api/v1/careers/${slug}`, revalidate);
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
  const careerPath = await getCareerPath(slug);
  if (!careerPath) return { title: "Career path not found" };

  const title = `${careerPath.title} career path`;
  return {
    title,
    description: careerPath.summary,
    openGraph: { title, description: careerPath.summary, type: "article" },
    twitter: { card: "summary_large_image", title, description: careerPath.summary },
  };
}

export default async function CareerDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const careerPath = await getCareerPath(slug);
  if (!careerPath) notFound();

  const sortedSkills = [...careerPath.required_skills].sort((a, b) => b.weight - a.weight);

  return (
    <SmoothScroll>
      <BreadcrumbJsonLd
        items={[
          { name: "Career paths", path: "/careers" },
          { name: careerPath.title, path: `/careers/${careerPath.slug}` },
        ]}
      />
      <Navbar />
      <main>
        <Section className="pb-16 pt-32 lg:pt-40">
          <Container>
            <Reveal>
              <Link
                href="/careers"
                className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
              >
                ← All career paths
              </Link>
              <h1 className="mt-4 max-w-[24ch] text-4xl font-semibold tracking-tighter text-foreground md:text-6xl">
                {careerPath.title}
              </h1>
              <p className="mt-5 max-w-[60ch] text-lg leading-relaxed text-muted-foreground">
                {careerPath.summary}
              </p>
              {careerPath.related_job_titles && careerPath.related_job_titles.length > 0 ? (
                <div className="mt-6 flex flex-wrap gap-2">
                  {careerPath.related_job_titles.map((jobTitle) => (
                    <span
                      key={jobTitle}
                      className="rounded-full border border-border-strong px-3 py-1 text-xs text-muted-foreground"
                    >
                      {jobTitle}
                    </span>
                  ))}
                </div>
              ) : null}
            </Reveal>

            <div className="mt-16 grid grid-cols-1 gap-10 lg:grid-cols-[1fr_22rem]">
              <Reveal delay={0.05}>
                <div className="flex flex-col gap-4 text-base leading-relaxed text-muted-foreground [&_em]:text-foreground [&_strong]:font-semibold [&_strong]:text-foreground">
                  <ReactMarkdown>{careerPath.description_md}</ReactMarkdown>
                </div>
              </Reveal>

              <Reveal delay={0.1}>
                <div className="rounded-xl border border-border bg-surface p-6">
                  <h2 className="text-sm font-medium text-foreground">Required skills</h2>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Sorted by how heavily each skill counts toward this role&apos;s gap analysis.
                  </p>
                  <ul className="mt-5 flex flex-col gap-3">
                    {sortedSkills.map(({ skill, weight, is_core }) => (
                      <li key={skill.id} className="flex items-center justify-between gap-3">
                        <Link
                          href={`/skills/${skill.slug}`}
                          className="text-sm text-foreground transition-colors hover:text-primary"
                        >
                          {skill.name}
                        </Link>
                        <span className="flex items-center gap-2">
                          {is_core ? (
                            <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-primary">
                              Core
                            </span>
                          ) : null}
                          <span className="h-1.5 w-12 overflow-hidden rounded-full bg-border">
                            <span
                              className={cn(
                                "block h-full rounded-full bg-primary transition-all duration-500"
                              )}
                              style={{ width: `${weight * 10}%` }}
                            />
                          </span>
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </Reveal>
            </div>

            {careerPath.related_career_paths.length > 0 ? (
              <div className="mt-24">
                <Reveal>
                  <h2 className="text-2xl font-semibold tracking-tight text-foreground">
                    Related career paths
                  </h2>
                </Reveal>
                <div className="mt-8 grid grid-cols-1 gap-5 md:grid-cols-3">
                  {careerPath.related_career_paths.map((related, index) => (
                    <CareerCard
                      key={related.id}
                      careerPath={related}
                      delay={Math.min(index * 0.05, 0.2)}
                    />
                  ))}
                </div>
              </div>
            ) : null}
          </Container>
        </Section>
      </main>
      <Footer />
    </SmoothScroll>
  );
}
