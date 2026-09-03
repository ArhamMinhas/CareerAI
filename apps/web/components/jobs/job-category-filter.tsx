"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

// The same 8 real role-query values Job.predicted_category is trained to classify into
// (docs/ML_PIPELINE.md §3 model 5, Phase 8 — app/scripts/ingest_adzuna_jobs.py's QUERIES).
const CATEGORIES = [
  "software engineer",
  "backend engineer",
  "frontend engineer",
  "full stack engineer",
  "machine learning engineer",
  "data scientist",
  "devops engineer",
  "product manager",
];

export function JobCategoryFilter() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const value = searchParams.get("category") ?? "";

  function handleChange(next: string) {
    const params = new URLSearchParams(searchParams);
    if (next) {
      params.set("category", next);
    } else {
      params.delete("category");
    }
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname);
  }

  return (
    <select
      value={value}
      onChange={(e) => handleChange(e.target.value)}
      className="h-11 rounded-lg border border-border-strong bg-background px-3 text-sm text-foreground outline-none transition-colors duration-200 hover:border-primary/40 focus:border-primary/60"
      aria-label="Filter jobs by category"
    >
      <option value="">All categories</option>
      {CATEGORIES.map((category) => (
        <option key={category} value={category}>
          {category.replace(/\b\w/g, (c) => c.toUpperCase())}
        </option>
      ))}
    </select>
  );
}
