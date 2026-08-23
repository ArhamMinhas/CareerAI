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
import { fetchPublic, PublicApiError } from "@/lib/public-api";
import { cardHoverMotion, cn } from "@/lib/utils";
import type { Skill } from "@/lib/types/profile";
import type { SkillDetail } from "@/lib/types/career-path";

export const revalidate = 3600;

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export async function generateStaticParams(): Promise<{ slug: string }[]> {
  // Pre-renders only the curated skills (docs/SEO.md §5's "SSG + ISR") — most skills in the
  // taxonomy have no `seo_summary` and still resolve at request time, they're just not worth
  // pre-building at scale (see `GET /api/v1/skills/curated`'s docstring). Falls back to an
  // empty list if the API isn't reachable during the build (e.g. CI's frontend-only job never
  // runs a backend) — `dynamicParams` defaults to true, so un-prerendered slugs still render
  // correctly on first request instead of failing the whole build.
  try {
    const curatedSkills = await fetchPublic<Skill[]>("/api/v1/skills/curated", revalidate);
    return curatedSkills.map((skill) => ({ slug: skill.slug }));
  } catch {
    return [];
  }
}

async function getSkill(slug: string): Promise<SkillDetail | null> {
  try {
    return await fetchPublic<SkillDetail>(`/api/v1/skills/${slug}`, revalidate);
  } catch (err) {
    if (err instanceof PublicApiError && err.status === 404) return null;
    throw err;
  }
}

function DefinedTermJsonLd({ skill }: { skill: SkillDetail }) {
  if (!skill.seo_summary) return null;
  const data = {
    "@context": "https://schema.org",
    "@type": "DefinedTerm",
    name: skill.name,
    description: skill.seo_summary,
    inDefinedTermSet: `${siteUrl}/skills`,
  };
  return (
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }} />
  );
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const skill = await getSkill(slug);
  if (!skill) return { title: "Skill not found" };

  const title = `${skill.name} skill`;
  const description = skill.seo_summary ?? `${skill.name} — part of CareerAI's skill taxonomy.`;
  return {
    title,
    description,
    openGraph: { title, description, type: "article" },
    twitter: { card: "summary_large_image", title, description },
  };
}

export default async function SkillDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const skill = await getSkill(slug);
  if (!skill) notFound();

  return (
    <SmoothScroll>
      <DefinedTermJsonLd skill={skill} />
      <BreadcrumbJsonLd
        items={[
          { name: "Home", path: "/" },
          { name: skill.name, path: `/skills/${skill.slug}` },
        ]}
      />
      <Navbar />
      <main>
        <Section className="pb-16 pt-32 lg:pt-40">
          <Container className="max-w-4xl">
            <Reveal>
              {skill.category ? (
                <p className="text-sm font-medium text-primary">{skill.category}</p>
              ) : null}
              <h1 className="mt-3 text-4xl font-semibold tracking-tighter text-foreground md:text-6xl">
                {skill.name}
              </h1>
              {skill.synonyms && skill.synonyms.length > 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">
                  Also known as: {skill.synonyms.join(", ")}
                </p>
              ) : null}
              {skill.seo_summary ? (
                <p className="mt-6 max-w-[65ch] text-lg leading-relaxed text-muted-foreground">
                  {skill.seo_summary}
                </p>
              ) : (
                <p className="mt-6 max-w-[65ch] text-lg leading-relaxed text-muted-foreground">
                  Part of CareerAI&apos;s skill taxonomy — used across resume analysis and
                  career-path gap comparisons.
                </p>
              )}
            </Reveal>

            {skill.career_paths.length > 0 ? (
              <Reveal delay={0.05} className="mt-14">
                <h2 className="text-sm font-medium text-foreground">Used in these career paths</h2>
                <div className="mt-4 flex flex-wrap gap-2">
                  {skill.career_paths.map((careerPath) => (
                    <Link
                      key={careerPath.slug}
                      href={`/careers/${careerPath.slug}`}
                      className={cn(
                        cardHoverMotion,
                        "rounded-full border border-border-strong px-4 py-2 text-sm text-foreground"
                      )}
                    >
                      {careerPath.title}
                    </Link>
                  ))}
                </div>
              </Reveal>
            ) : null}

            {skill.related_skills.length > 0 ? (
              <Reveal delay={0.1} className="mt-14">
                <h2 className="text-sm font-medium text-foreground">Related skills</h2>
                <div className="mt-4 flex flex-wrap gap-2">
                  {skill.related_skills.map((related) => (
                    <Link
                      key={related.id}
                      href={`/skills/${related.slug}`}
                      className={cn(
                        cardHoverMotion,
                        "rounded-full border border-border px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
                      )}
                    >
                      {related.name}
                    </Link>
                  ))}
                </div>
              </Reveal>
            ) : null}
          </Container>
        </Section>
      </main>
      <Footer />
    </SmoothScroll>
  );
}
