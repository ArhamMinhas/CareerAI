# CareerAI — SEO & Discoverability Strategy

Status: Phase 0 design. Foundational technical SEO (metadata, sitemap, robots.txt, structured
data) is built in Phase 2 alongside the landing page so it's never bolted on after launch;
`/careers/[slug]` and `/skills/[slug]` ship in Phase 6, `/jobs/[id]` and `/companies/[id]` in
Phase 7, `/resources/[slug]` in Phase 9 (RAG); baseline search-console/analytics wiring happens
in Phase 16 (initial deployment), and the full rollout — every content type live with complete
structured data, Core Web Vitals budgets on all public routes, and production monitoring — is
the explicit focus of **Phase 17 (Cloud + SEO + Production Deployment)**. See
[ROADMAP.md](./ROADMAP.md).

This document exists so that once CareerAI is deployed, it is actually **findable** — indexed
correctly by Google/Bing, rendered properly when shared, and fast enough to rank. It complements
[UI_ARCHITECTURE.md](./UI_ARCHITECTURE.md) (rendering strategy SEO depends on) and
[DEPLOYMENT.md](./DEPLOYMENT.md) (where the domain/DNS/HTTPS steps live).

## 1. What gets indexed vs. what doesn't

| Surface | Indexable? | Rendering | Backing data |
|---|---|---|---|
| `/` marketing landing page | Yes | SSG | static content |
| `/careers`, `/careers/[slug]` (e.g. `/careers/ai-engineer`) | Yes | SSG + ISR revalidate | `career_paths` ([DATABASE.md §2.6](./DATABASE.md#26-public-content--seo)) |
| `/skills/[slug]` (e.g. `/skills/python`, `/skills/machine-learning`) | Yes | SSG + ISR revalidate | `skills` |
| `/jobs`, `/jobs/[id]` | Yes — the highest-value programmatic SEO surface (real, unique, frequently-updated content) | ISR — see §5 | `jobs` |
| `/companies/[id]` | Yes | ISR revalidate | `companies` |
| `/resources/[slug]` | Yes | SSG + ISR revalidate | `resources` (same content that feeds RAG — see [DATABASE.md §2.6](./DATABASE.md#26-public-content--seo)) |
| `/dashboard`, `/resume`, `/analytics`, `/interviews`, `/settings`, and the rest of the authenticated app (`/profile`, `/skills` *app view*, `/career`, `/matches`, `/roadmap`, `/interviews/[id]`) | **No** — private, personalized, behind auth | `noindex`, excluded from sitemap |
| `/admin/*` | **No** | `noindex`, excluded from sitemap, also blocked in `robots.txt` |
| `/api/*` | **No** | Blocked in `robots.txt`; not HTML anyway |

Note the naming overlap is intentional but scoped carefully: `/skills` (exact path, under the
authenticated app shell) is the user's personal skill inventory; `/skills/[slug]` (dynamic
segment) is the public SEO glossary page for a single skill, reading the same `skills` table.
Next.js resolves these as distinct routes with no collision (`app/skills/page.tsx` vs.
`app/skills/[slug]/page.tsx`), and the authenticated app never defines a matching `/skills/[id]`
route of its own — a per-skill authenticated deep-dive, if one is added later, must live under a
different path (e.g. `/dashboard/skills/[id]`) precisely to avoid that ambiguity.

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

Generated, not hand-maintained, as a sitemap **index** over one sub-sitemap per content type —
`sitemap.xml` links to `sitemap/static.xml`, `sitemap/jobs.xml`, `sitemap/careers.xml`,
`sitemap/companies.xml`, `sitemap/resources.xml`. Jobs get their own paginated sub-sitemap
(`sitemap/jobs/0.xml`, `sitemap/jobs/1.xml`, ...) since that's the largest and fastest-changing
set and, once it exceeds the ~50k URL single-file limit, needs pagination the other content
types won't for a long time. Every entry is generated directly from its table
(`WHERE published = true` for `career_paths`/`resources`, all non-deleted rows for `jobs`), so
the sitemap never needs manual regeneration and can't drift from what's actually live.
`lastModified` is sourced from each row's `updated_at` (`jobs.updated_at`,
`resources.updated_at`, ...) so crawlers prioritize re-crawling recently changed content.

### 2.4 Structured data (JSON-LD)

Injected via a small `<script type="application/ld+json">` per relevant page. `Organization` and
`BreadcrumbList` are applied broadly (site-wide identity + hierarchy signal on every deep page);
the rest are specific to what the page actually is:

| Page | Schema.org type | Why |
|---|---|---|
| Every page (root layout) | `Organization` | Site-wide brand identity — knowledge panel eligibility, consistent logo/name across all rich results |
| `/` | `WebSite` (with `SearchAction` if on-site search ships) | Sitelinks search box eligibility |
| `/jobs/[id]` | `JobPosting` | Eligibility for Google for Jobs — the single highest-leverage structured data on this project, since it makes every job page a candidate for a rich, high-CTR listing |
| `/companies/[id]` | `Organization` (company-specific instance, distinct from the site-wide one) | Company knowledge panel, consistent entity linking from its `JobPosting.hiringOrganization` references |
| `/careers/[slug]` | `BreadcrumbList` + descriptive metadata; `Occupation` where the field's schema support is worth the maintenance cost | Career-path pages are less standardized in Schema.org than jobs — `Occupation` (with `estimatedSalary`, `skills`) is the closest fit and is treated as an incremental enhancement, not a Phase 6 launch blocker |
| `/skills/[slug]` | `DefinedTerm` (skill name + description, part of a site-wide `DefinedTermSet`) | Correct semantic fit for a glossary/definition page; supports rich snippet eligibility for "what is X" queries |
| `/resources/[slug]` | `Article` (`headline`, `datePublished` ← `published_at`, `dateModified` ← `updated_at`, `author`/`publisher` ← site `Organization`) | Standard article rich-result eligibility |
| FAQ section on landing page (and any `/resources/[slug]` page structured as Q&A) | `FAQPage` | FAQ rich results |
| `/jobs`, `/jobs/[id]`, `/careers/[slug]`, `/companies/[id]`, `/resources/[slug]` | `BreadcrumbList` | Breadcrumb rich results, clearer site hierarchy signal |

`JobPosting` fields map directly from the `jobs`/`companies` tables in
[DATABASE.md](./DATABASE.md) (`title`, `description`, `datePosted` ← `posted_at`,
`employmentType`, `hiringOrganization` ← `companies.name`, `jobLocation`, `baseSalary` ←
`salary_min`/`salary_max`/`currency`) — no separate content authoring needed, so structured data
stays correct automatically as the `jobs` table updates. `validThrough` is derived from job
status so expired postings stop appearing as active listings in search results. `Occupation`,
`DefinedTerm`, and `Article` fields similarly map straight from `career_paths`, `skills`, and
`resources` respectively — structured data is always generated from the same row that renders
the page, never hand-authored separately and left to drift.

### 2.5 Dynamic Open Graph images

One `opengraph-image.tsx` (Next.js `ImageResponse` / `@vercel/og`) route per public content
type — `/jobs/[id]`, `/careers/[slug]`, `/companies/[id]`, `/resources/[slug]` — each generating
a branded share-card (title + the field that matters for that type: company/location for jobs,
category for resources) at request time, cached at the edge. A shared card template/component
keeps the visual style consistent across content types rather than four one-off designs.

### 2.6 Twitter/X Cards

Set alongside Open Graph in the same `generateMetadata()` call (`twitter: { card:
"summary_large_image", title, description, images }`), not a separate implementation path — the
OG image route from §2.5 is reused as the Twitter image so there's one image asset per page, not
two. Root layout sets a default card as a fallback for any page that doesn't override it.

### 2.7 Image optimization (WebP/AVIF)

All content images go through `next/image`, which serves AVIF where the browser supports it,
falling back to WebP, then the original format — no manually-maintained multi-format image
pipeline. Applies to job/company logos, resource article images, and any landing-page imagery;
the 3D hero canvas and decorative SVGs are exempt (not raster images). Every `next/image` usage
sets explicit `width`/`height` (or `fill` with a sized container) so images never cause layout
shift, tying directly into the CLS budget in §4.

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
- **Internal linking / topic clusters:** the five public content types cross-link deliberately
  rather than sitting in isolation — a `/careers/[slug]` page links out to its required
  `/skills/[slug]` pages (via `career_path_skills`) and to matching `/jobs` results; a
  `/skills/[slug]` page links to the `/careers/[slug]` pages that require it and to
  `/resources/[slug]` articles about that skill; a `/jobs/[id]` page links to its
  `/companies/[id]` page and to related jobs (same company, same skill cluster) via the
  embedding similarity already computed for recommendations
  ([AI_ARCHITECTURE.md §5](./AI_ARCHITECTURE.md#5-embeddings--vector-search)). This turns
  "career → skill → job → company → resource" into a real crawlable graph instead of five
  disconnected page types, which is both better for users and the single biggest lever for
  getting the long-tail pages (individual skills, individual careers) discovered and ranked —
  entirely a byproduct of relationships the product already models in
  [DATABASE.md §2.6](./DATABASE.md#26-public-content--seo), not extra content work.
- **Alt text:** required on every content image (enforced by lint rule / component prop, not a
  convention that quietly rots); the 3D hero canvas and decorative visuals get `aria-hidden` and
  contribute no alt text burden since they're non-informational.
- **URL structure:** clean, human-readable, stable slugs across every content type —
  `/careers/ai-engineer`, `/skills/machine-learning`, `/resources/how-to-answer-system-design-questions`
  (from each table's `slug` column), and `/jobs/senior-ai-engineer-acme-corp-<short-id>` (title
  slug + short ID, since job titles aren't unique the way a curated career/skill/article slug is
  — the short ID keeps the URL unique and stable even if the title text is edited).

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

- Marketing pages (`/`): fully static (SSG) at build time, revalidated on deploy.
- `/jobs`, `/jobs/[id]`: **Incremental Static Regeneration**, short revalidate interval (e.g.
  5–15 min) — the highest-churn content, so newly ingested jobs and status changes (closed
  postings) reach crawlers without a full redeploy.
- `/careers/[slug]`, `/skills/[slug]`, `/companies/[id]`, `/resources/[slug]`: ISR with a longer
  revalidate interval (e.g. hours, not minutes) — this content changes far less often than job
  listings, so the freshness/build-cost trade-off favors a slower revalidation cadence; an
  on-demand `revalidatePath()` call triggered from the admin content editor (Phase 13) handles
  the rare case of needing an immediate update (e.g. correcting a published article).
- No SEO-relevant content is ever client-fetched-only (i.e. rendered exclusively via
  `useEffect` + client-side `fetch`) — crawlers must see real content in the initial HTML.

## 6. Search engine setup (post-deployment checklist)

Baseline steps execute once a production domain exists (Phase 16); items 4–7 are revisited and
made durable in Phase 17 alongside the full production monitoring stack. See
[DEPLOYMENT.md §6](./DEPLOYMENT.md#6-domain-https-and-seo-go-live-checklist):

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
