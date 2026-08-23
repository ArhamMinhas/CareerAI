const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

/**
 * A company-specific `Organization` instance (docs/SEO.md §2.4) — distinct from the site-wide
 * one in the root layout, so `JobPosting.hiringOrganization`'s `sameAs` link resolves to an
 * entity Google can build a knowledge panel from, not CareerAI's own.
 */
export function OrganizationJsonLd({
  name,
  slug,
  description,
  logoUrl,
}: {
  name: string;
  slug: string;
  description: string | null;
  logoUrl: string | null;
}) {
  const data = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name,
    url: `${siteUrl}/companies/${slug}`,
    description: description ?? undefined,
    logo: logoUrl ?? undefined,
  };
  return (
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }} />
  );
}
