import type { Metadata } from "next";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { SmoothScroll } from "@/components/layout/smooth-scroll";
import { Section } from "@/components/ui/section";
import { Container } from "@/components/ui/container";
import { Reveal } from "@/components/motion/reveal";
import { JobSearchInput } from "@/components/jobs/job-search-input";
import { JobCategoryFilter } from "@/components/jobs/job-category-filter";
import { JobList } from "@/components/jobs/job-list";
import { PublicApiError } from "@/lib/public-api";
import type { Job } from "@/lib/types/job";

// Short revalidate (docs/SEO.md §5: jobs are "the highest-churn content" — 5-15 min, not the
// hours-long interval careers/skills/companies use) — new postings and status changes should
// show up quickly rather than sitting behind an hours-long ISR window.
export const revalidate = 600;

const title = "Jobs";
const description =
  "Browse open roles with real, structured postings — searchable by title, company, or keyword.";

export const metadata: Metadata = {
  title,
  description,
  openGraph: { title, description, type: "website" },
  twitter: { card: "summary_large_image", title, description },
};

type JobsEnvelope = { data: Job[]; meta: { next_cursor: string | null } };

async function getJobs(
  q: string,
  category: string,
): Promise<{ jobs: Job[]; nextCursor: string | null }> {
  try {
    // `fetchPublic` only returns `data`, but this page also needs `meta.next_cursor` for the
    // "Load more" affordance, so this reads the envelope directly rather than going through it.
    const apiBase =
      process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const params = new URLSearchParams({ limit: "20" });
    if (q) params.set("q", q);
    if (category) params.set("category", category);
    const response = await fetch(`${apiBase}/api/v1/jobs?${params.toString()}`, {
      next: { revalidate },
    });
    if (!response.ok) throw new PublicApiError(response.status, "Request to /jobs failed");
    const envelope = (await response.json()) as JobsEnvelope;
    return { jobs: envelope.data, nextCursor: envelope.meta.next_cursor };
  } catch (err) {
    if (err instanceof PublicApiError || err instanceof TypeError) return { jobs: [], nextCursor: null };
    throw err;
  }
}

export default async function JobsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; category?: string }>;
}) {
  const { q = "", category = "" } = await searchParams;
  const { jobs, nextCursor } = await getJobs(q, category);

  return (
    <SmoothScroll>
      <Navbar />
      <main>
        <Section className="pb-16 pt-24 lg:pt-28">
          <Container>
            <Reveal>
              <p className="text-sm font-medium text-primary">Jobs</p>
              <h1 className="mt-3 max-w-[24ch] text-4xl font-semibold tracking-tighter text-foreground md:text-6xl">
                Real roles, matched to your real skills
              </h1>
              <p className="mt-5 max-w-[60ch] text-lg leading-relaxed text-muted-foreground">
                Every posting here is structured, searchable data — the same postings CareerAI&apos;s
                hybrid matching engine ranks against your resume once you sign in.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <JobSearchInput />
                <JobCategoryFilter />
              </div>
            </Reveal>

            <div className="mt-12">
              {/* `key` forces a remount on every search/filter change — JobList seeds its job
              list via `useState(initialJobs)`, which only runs on mount, so without this the
              client component would keep showing the first query's results forever. */}
              <JobList
                key={`${q}-${category}`}
                initialJobs={jobs}
                initialNextCursor={nextCursor}
                q={q}
                category={category}
              />
            </div>
          </Container>
        </Section>
      </main>
      <Footer />
    </SmoothScroll>
  );
}
