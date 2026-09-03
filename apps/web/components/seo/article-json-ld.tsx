const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

/** `Article` structured data (docs/SEO.md §2.4) for `/resources/[slug]` — the only content type
 * so far that's genuinely article-shaped prose, unlike `/careers/[slug]` (a role profile) or
 * `/skills/[slug]` (a reference definition). Not `FaqJsonLd`: this content is guide/how-to
 * prose, not curated Q&A pairs, and synthesizing fake FAQ pairs just to populate that schema
 * would be exactly the kind of hand-authored-and-drifting content docs/SEO.md warns against. */
export function ArticleJsonLd({
  title,
  description,
  path,
  dateModified,
}: {
  title: string;
  description: string;
  path: string;
  dateModified: string;
}) {
  const data = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: title,
    description,
    url: `${siteUrl}${path}`,
    dateModified,
  };
  return (
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }} />
  );
}
