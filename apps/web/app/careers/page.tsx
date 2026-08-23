import type { Metadata } from "next";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { SmoothScroll } from "@/components/layout/smooth-scroll";
import { Section } from "@/components/ui/section";
import { Container } from "@/components/ui/container";
import { Reveal } from "@/components/motion/reveal";
import { CareerCard } from "@/components/careers/career-card";
import { fetchPublic } from "@/lib/public-api";
import type { CareerPath } from "@/lib/types/career-path";

// ISR — this content changes far less often than jobs (docs/SEO.md §5), so a long revalidate
// interval is correct here, not a short one.
export const revalidate = 3600;

const title = "Career paths";
const description =
  "Explore curated career paths — the exact required-skill profiles CareerAI's skill-gap engine compares your skills against.";

export const metadata: Metadata = {
  title,
  description,
  openGraph: { title, description, type: "website" },
  twitter: { card: "summary_large_image", title, description },
};

export default async function CareersPage() {
  const careerPaths = await fetchPublic<CareerPath[]>("/api/v1/careers", revalidate);

  return (
    <SmoothScroll>
      <Navbar />
      <main>
        <Section className="pb-16 pt-32 lg:pt-40">
          <Container>
            <Reveal>
              <p className="text-sm font-medium text-primary">Career paths</p>
              <h1 className="mt-3 max-w-[24ch] text-4xl font-semibold tracking-tighter text-foreground md:text-6xl">
                Find the role, see the gap
              </h1>
              <p className="mt-5 max-w-[60ch] text-lg leading-relaxed text-muted-foreground">
                Each path below is a curated, weighted skill profile — the same one
                CareerAI&apos;s skill-gap engine diffs your profile against once you pick a
                target role.
              </p>
            </Reveal>

            <div className="mt-16 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
              {careerPaths.map((careerPath, index) => (
                <CareerCard
                  key={careerPath.id}
                  careerPath={careerPath}
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
