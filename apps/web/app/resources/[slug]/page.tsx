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
import { ResourceCard } from "@/components/resources/resource-card";
import { BreadcrumbJsonLd } from "@/components/seo/breadcrumb-json-ld";
import { ArticleJsonLd } from "@/components/seo/article-json-ld";
import { fetchPublic, PublicApiError } from "@/lib/public-api";
import type { Resource, ResourceDetail } from "@/lib/types/resource";

export const revalidate = 3600;

export async function generateStaticParams(): Promise<{ slug: string }[]> {
  // Falls back to an empty list if the API isn't reachable during the build — same reasoning as
  // /careers/[slug]; `dynamicParams` defaults to true, so un-prerendered slugs still render
  // correctly on first request.
  try {
    const resources = await fetchPublic<Resource[]>("/api/v1/resources", revalidate);
    return resources.map((resource) => ({ slug: resource.slug }));
  } catch {
    return [];
  }
}

async function getResource(slug: string): Promise<ResourceDetail | null> {
  try {
    return await fetchPublic<ResourceDetail>(`/api/v1/resources/${slug}`, revalidate);
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
  const resource = await getResource(slug);
  if (!resource) return { title: "Resource not found" };

  return {
    title: resource.title,
    description: resource.summary,
    openGraph: { title: resource.title, description: resource.summary, type: "article" },
    twitter: { card: "summary_large_image", title: resource.title, description: resource.summary },
  };
}

export default async function ResourceDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const resource = await getResource(slug);
  if (!resource) notFound();

  return (
    <SmoothScroll>
      <BreadcrumbJsonLd
        items={[
          { name: "Resources", path: "/resources" },
          { name: resource.title, path: `/resources/${resource.slug}` },
        ]}
      />
      <ArticleJsonLd
        title={resource.title}
        description={resource.summary}
        path={`/resources/${resource.slug}`}
        dateModified={resource.updated_at}
      />
      <Navbar />
      <main>
        <Section className="pb-16 pt-24 lg:pt-28">
          <Container>
            <Reveal>
              <Link
                href="/resources"
                className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
              >
                ← All resources
              </Link>
              {resource.category ? (
                <p className="mt-4 text-sm font-medium text-primary">{resource.category}</p>
              ) : null}
              <h1 className="mt-3 max-w-[32ch] text-4xl font-semibold tracking-tighter text-foreground md:text-6xl">
                {resource.title}
              </h1>
              <p className="mt-5 max-w-[60ch] text-lg leading-relaxed text-muted-foreground">
                {resource.summary}
              </p>
              {resource.tags && resource.tags.length > 0 ? (
                <div className="mt-6 flex flex-wrap gap-2">
                  {resource.tags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full border border-border-strong px-3 py-1 text-xs text-muted-foreground"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              ) : null}
            </Reveal>

            <Reveal delay={0.05} className="mt-16 max-w-[70ch]">
              <div className="flex flex-col gap-4 text-base leading-relaxed text-muted-foreground [&_em]:text-foreground [&_h2]:mt-8 [&_h2]:text-2xl [&_h2]:font-semibold [&_h2]:tracking-tight [&_h2]:text-foreground [&_strong]:font-semibold [&_strong]:text-foreground">
                <ReactMarkdown>{resource.body_md}</ReactMarkdown>
              </div>
            </Reveal>

            {resource.related_resources.length > 0 ? (
              <div className="mt-16">
                <Reveal>
                  <h2 className="text-2xl font-semibold tracking-tight text-foreground">
                    Related resources
                  </h2>
                </Reveal>
                <div className="mt-8 grid grid-cols-1 gap-5 md:grid-cols-3">
                  {resource.related_resources.map((related, index) => (
                    <ResourceCard
                      key={related.id}
                      resource={related}
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
