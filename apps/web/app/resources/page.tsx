import type { Metadata } from "next";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { SmoothScroll } from "@/components/layout/smooth-scroll";
import { Section } from "@/components/ui/section";
import { Container } from "@/components/ui/container";
import { Reveal } from "@/components/motion/reveal";
import { ResourceCard } from "@/components/resources/resource-card";
import { fetchPublic, PublicApiError } from "@/lib/public-api";
import type { Resource } from "@/lib/types/resource";

// ISR — curated guide content changes far less often than jobs (docs/SEO.md §5), same reasoning
// as /careers.
export const revalidate = 3600;

const title = "Resources";
const description =
  "Practical, specific guides on resumes, skills, interviewing, and negotiation — the same knowledge base CareerAI's Ask AI feature grounds its answers in.";

export const metadata: Metadata = {
  title,
  description,
  openGraph: { title, description, type: "website" },
  twitter: { card: "summary_large_image", title, description },
};

async function getResources(): Promise<Resource[]> {
  try {
    return await fetchPublic<Resource[]>("/api/v1/resources", revalidate);
  } catch (err) {
    // Degrade to an empty list rather than failing the whole page/build — same reasoning as
    // /careers's index page.
    if (err instanceof PublicApiError || err instanceof TypeError) return [];
    throw err;
  }
}

export default async function ResourcesPage() {
  const resources = await getResources();

  return (
    <SmoothScroll>
      <Navbar />
      <main>
        <Section className="pb-16 pt-24 lg:pt-28">
          <Container>
            <Reveal>
              <p className="text-sm font-medium text-primary">Resources</p>
              <h1 className="mt-3 max-w-[24ch] text-4xl font-semibold tracking-tighter text-foreground md:text-6xl">
                Guides worth actually reading
              </h1>
              <p className="mt-5 max-w-[60ch] text-lg leading-relaxed text-muted-foreground">
                Specific, practical advice on resumes, skills, interviewing, and negotiation —
                curated content CareerAI&apos;s Ask AI feature grounds its answers in, not
                generic filler.
              </p>
            </Reveal>

            <div className="mt-16 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
              {resources.map((resource, index) => (
                <ResourceCard
                  key={resource.id}
                  resource={resource}
                  delay={Math.min(index * 0.05, 0.3)}
                />
              ))}
            </div>
          </Container>
        </Section>
      </main>
      <Footer />
    </SmoothScroll>
  );
}
