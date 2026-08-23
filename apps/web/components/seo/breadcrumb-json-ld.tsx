const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

/** `BreadcrumbList` structured data (docs/SEO.md §2.4) — shared across every public content
 * page that needs one (`/careers/[slug]`, `/skills/[slug]`, and future `/jobs/[id]`,
 * `/companies/[id]`, `/resources/[slug]`) so the shape stays identical rather than
 * hand-rolled per page. */
export function BreadcrumbJsonLd({ items }: { items: { name: string; path: string }[] }) {
  const data = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: `${siteUrl}${item.path}`,
    })),
  };
  return (
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }} />
  );
}
