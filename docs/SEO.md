# CareerAI — SEO & Discoverability Strategy

Status: Phase 0 design. Foundational technical SEO (metadata, sitemap, robots.txt, structured
data) is built in Phase 2 alongside the landing page so it's never bolted on after launch;
programmatic SEO for job pages ships in Phase 7 (job recommendation) once `/jobs/[id]` exists;
search-console/analytics wiring happens in Phase 16 (production deployment). See
[ROADMAP.md](./ROADMAP.md).

This document exists so that once CareerAI is deployed, it is actually **findable** — indexed
correctly by Google/Bing, rendered properly when shared, and fast enough to rank. It complements
[UI_ARCHITECTURE.md](./UI_ARCHITECTURE.md) (rendering strategy SEO depends on) and
[DEPLOYMENT.md](./DEPLOYMENT.md) (where the domain/DNS/HTTPS steps live).

## 1. What gets indexed vs. what doesn't

| Surface | Indexable? | Rendering |
|---|---|---|
| `/` marketing landing page | Yes | Server Component, statically generated (SSG) |
| `/jobs`, `/jobs/[id]` | Yes — this is the highest-value programmatic SEO surface (real, unique, frequently-updated content) | Server-rendered (ISR — see §5) |
| Public career-guide / RAG knowledge-base content (future blog/guides surface) | Yes | SSG/ISR |
| `/dashboard`, `/profile`, `/resume/*`, `/skills`, `/career`, `/matches`, `/roadmap`, `/interviews/*`, `/analytics`, `/settings` | **No** — private, personalized, behind auth | `noindex`, excluded from sitemap |
| `/admin/*` | **No** | `noindex`, excluded from sitemap, also blocked in `robots.txt` |
| `/api/*` | **No** | Blocked in `robots.txt`; not HTML anyway |

Rule of thumb: only server-rendered, publicly-accessible, unique content is a page we want
indexed. Anything requiring auth is explicitly marked `noindex` — indexing a login-gated page
that Google can't actually render is worse than not listing it at all.

## 2. Technical SEO implementation (Next.js App Router)

### 2.1 Metadata API

Every indexable route exports `generateMetadata()` (dynamic routes) or a static `metadata`
object, rather than manual `<head>` tags:

```ts
export async function generateMetadata({ params }): Promise<Metadata> {
  const job = await getJob(params.id);
  return {
    title: `${job.title} at ${job.company.name} | CareerAI`,
    description: job.summary.slice(0, 155),
    alternates: { canonical: `${SITE_URL}/jobs/${job.id}` },
    openGraph: {
      title: job.title,
      description: job.summary,
      url: `${SITE_URL}/jobs/${job.id}`,
      images: [`${SITE_URL}/jobs/${job.id}/opengraph-image`],
    },
    twitter: { card: "summary_large_image" },
  };
}
```

- A root `app/layout.tsx` metadata template sets the site-wide title template
  (`"%s | CareerAI"`), default description, `metadataBase`, and `robots` defaults.
- Every private route's layout sets `robots: { index: false, follow: false }` explicitly — not
  relying on omission.
- `<link rel="canonical">` is set on every page (via `alternates.canonical`) to avoid duplicate-
  content penalties from query-string variants (`/jobs?sort=...`).

### 2.2 `robots.txt` (generated via `app/robots.ts`)

```
User-agent: *
Allow: /
Disallow: /dashboard
Disallow: /profile
Disallow: /resume
Disallow: /skills
Disallow: /career
Disallow: /matches
Disallow: /roadmap
Disallow: /interviews
Disallow: /analytics
Disallow: /settings
Disallow: /admin
Disallow: /api

Sitemap: https://careerai.example.com/sitemap.xml
```

### 2.3 Sitemap (`app/sitemap.ts`)

Generated, not hand-maintained: static marketing routes plus a **paginated dynamic sitemap
index** over `jobs` (and future public knowledge-base articles), since job listings are the
largest and most frequently changing indexable set. Next.js supports sitemap generator
functions that can return multiple sitemap files (`sitemap.xml`, `sitemap/0.xml`, ...) once the
URL count exceeds the ~50k single-file limit — the job sitemap route paginates by
`created_at`/`id` directly from the `jobs` table so it never needs to be manually regenerated.
Each entry includes `lastModified` (from `jobs.updated_at`) so crawlers can prioritize re-crawls
of recently changed postings.

### 2.4 Structured data (JSON-LD)

Injected via a small `<script type="application/ld+json">` per relevant page:

| Page | Schema.org type | Why |
|---|---|---|
| `/` | `Organization`, `WebSite` (with `SearchAction` if on-site search ships) | Brand knowledge panel eligibility, sitelinks search box |
| `/jobs/[id]` | `JobPosting` | Eligibility for Google for Jobs — the single highest-leverage structured data on this project, since it makes every job page a candidate for a rich, high-CTR listing |
| FAQ section on landing page | `FAQPage` | FAQ rich results |
| `/jobs`, `/jobs/[id]` | `BreadcrumbList` | Breadcrumb rich results, clearer site hierarchy signal |

`JobPosting` fields map directly from the `jobs`/`companies` tables in
[DATABASE.md](./DATABASE.md) (`title`, `description`, `datePosted` ← `posted_at`,
`employmentType`, `hiringOrganization` ← `companies.name`, `jobLocation`, `baseSalary` ←
`salary_min`/`salary_max`/`currency`) — no separate content authoring needed, so structured data
stays correct automatically as the `jobs` table updates. `validThrough` is derived from job
status so expired postings stop appearing as active listings in search results.

### 2.5 Dynamic Open Graph images

`app/jobs/[id]/opengraph-image.tsx` (Next.js `ImageResponse` / `@vercel/og`) generates a
branded share-card per job (title, company, location) at request time, cached — so a job link
shared on LinkedIn/Slack/Twitter renders a real preview instead of a generic screenshot.

## 3. On-page / content SEO

- **Heading hierarchy:** one `<h1>` per page (the page's primary subject — job title, section
  headline), logical `<h2>`/`<h3>` nesting for landing-page sections; never skipped levels for
  styling convenience (this doubles as the accessibility heading structure in
  [UI_ARCHITECTURE.md §8](./UI_ARCHITECTURE.md#8-accessibility)).
- **Keyword intent mapping** for the landing page sections (spec §10): hero/product intro target
  "AI career platform" / "career intelligence" head terms; resume-intelligence and skill-gap
  sections target mid-funnel terms ("resume score checker", "skill gap analysis tool", "AI
  interview practice"); job pages target long-tail, highly specific queries ("[title] jobs at
  [company]", "[title] remote jobs") purely as a byproduct of accurate structured content — no
  keyword stuffing.
- **Internal linking:** landing page sections link to their corresponding feature/marketing
  detail anchors; job listing pages cross-link to related jobs (same company, same skill
  cluster) using the existing embedding similarity from
  [AI_ARCHITECTURE.md §5](./AI_ARCHITECTURE.md#5-embeddings--vector-search) — SEO value is a
  free side effect of a feature that already exists for recommendations.
- **Alt text:** required on every content image (enforced by lint rule / component prop, not a
  convention that quietly rots); the 3D hero canvas and decorative visuals get `aria-hidden` and
  contribute no alt text burden since they're non-informational.
- **URL structure:** clean, human-readable slugs (`/jobs/senior-ai-engineer-acme-corp-<short-id>`
  rather than a bare UUID) — the short ID keeps URLs unique and stable even if a title is edited.

## 4. Core Web Vitals & performance as a ranking factor

Google's ranking signals include LCP, INP, and CLS. This is why
[UI_ARCHITECTURE.md §10](./UI_ARCHITECTURE.md#10-performance-budget) is not purely a UX concern:

- LCP: landing hero's largest content (headline text, not the 3D canvas) must paint fast — the
  3D scene is lazy-loaded *after* first paint, never blocking it.
- CLS: image/embed dimensions are always reserved (`next/image` requires this by default);
  skeleton loading states occupy the same layout space as their resolved content.
- INP: avoid long main-thread tasks on interaction — heavy chart/3D work is deferred or
  virtualized; route transitions stay snappy per the animation rules in
  [UI_ARCHITECTURE.md §5](./UI_ARCHITECTURE.md#5-animation-system).

Tracked in CI via Lighthouse CI starting Phase 15 (production hardening), with budgets that fail
the build if LCP/CLS regress past a threshold on the marketing routes specifically (the
dashboard's budget is looser since it isn't an SEO surface).

## 5. Rendering & freshness strategy for indexable routes

- Marketing pages: fully static (SSG) at build time, revalidated on deploy.
- `/jobs` and `/jobs/[id]`: **Incremental Static Regeneration** — statically served for
  performance/SEO, revalidated on a short interval (e.g. 5–15 min) so newly ingested jobs and
  status changes (closed postings) reach crawlers without a full redeploy.
- No SEO-relevant content is ever client-fetched-only (i.e. rendered exclusively via
  `useEffect` + client-side `fetch`) — crawlers must see real content in the initial HTML.

## 6. Search engine setup (post-deployment checklist)

Executed once a production domain exists (Phase 16, [DEPLOYMENT.md](./DEPLOYMENT.md)):

1. **Domain/canonicalization:** pick one canonical host (`https://careerai.example.com`, no
   `www`/non-`www` split) and 301-redirect the other variant; enforce HTTPS redirect at the edge.
2. **Google Search Console:** verify ownership (DNS TXT record or the
   `google-site-verification` meta tag driven by `GOOGLE_SITE_VERIFICATION`), submit
   `sitemap.xml`, monitor Coverage and Core Web Vitals reports.
3. **Bing Webmaster Tools:** verify + submit sitemap (Bing also powers a meaningful share of
   search + is a low-effort addition once Search Console is wired up).
4. **`llms.txt` / AI crawler consideration:** optionally publish a plain-language `llms.txt`
   summarizing the product for AI answer engines, mirroring the intent of `robots.txt` but for
   LLM-based discovery — low cost, forward-looking given how career-search queries increasingly
   route through AI assistants.
5. **Analytics:** privacy-respecting analytics (e.g. Plausible, or GA4 if preferred) wired via
   `NEXT_PUBLIC_ANALYTICS_ID`, loaded only after cookie-consent where required by jurisdiction.
6. **Broken-link / 404 handling:** custom `not-found.tsx` for genuinely missing content, and a
   real `410 Gone`-equivalent (or redirect to `/jobs`) for expired job postings rather than a
   generic soft-404, so crawlers correctly deprioritize removed listings instead of retrying them.
7. **Ongoing monitoring:** Search Console coverage/index errors and Core Web Vitals are checked
   as part of the admin system-health surface (spec §38/§40) rather than a separate manual habit.

## 7. Environment variables

Documented in [.env.example](../.env.example): `NEXT_PUBLIC_SITE_URL` (canonical origin used in
metadata/sitemap/canonical URLs — must match the deployed domain exactly), `GOOGLE_SITE_VERIFICATION`,
`BING_SITE_VERIFICATION`, `NEXT_PUBLIC_ANALYTICS_ID`.

## 8. Explicit non-goals for Phase 0–2

Multi-locale/hreflang, AMP, and paid-search landing-page variants are out of scope until there's
a concrete need — added here only as a placeholder so they're a deliberate future decision, not
an oversight.
