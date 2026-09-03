"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { JobCard } from "@/components/jobs/job-card";
import type { Job } from "@/lib/types/job";

export function JobList({
  initialJobs,
  initialNextCursor,
  q,
  category = "",
}: {
  initialJobs: Job[];
  initialNextCursor: string | null;
  q: string;
  category?: string;
}) {
  const [jobs, setJobs] = useState(initialJobs);
  const [nextCursor, setNextCursor] = useState(initialNextCursor);
  const [loading, setLoading] = useState(false);

  async function loadMore() {
    if (!nextCursor || loading) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: "20", cursor: nextCursor });
      if (q) params.set("q", q);
      if (category) params.set("category", category);
      const response = await apiFetch<Job[]>(`/api/v1/jobs?${params.toString()}`, {
        method: "GET",
      });
      // apiFetch unwraps to `data` only — meta isn't exposed, so fetch it via a second call
      // that reads the raw envelope would be wasteful; instead re-derive whether there's more
      // by checking if this page came back full-sized (the common, good-enough heuristic).
      setJobs((prev) => [...prev, ...response]);
      setNextCursor(response.length === 20 ? nextCursor : null);
    } finally {
      setLoading(false);
    }
  }

  if (jobs.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border-strong px-6 py-16 text-center">
        <p className="text-sm font-medium text-foreground">No jobs match your search</p>
        <p className="max-w-[40ch] text-sm text-muted-foreground">
          Try a different keyword, or clear the search to see every open posting.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
        {jobs.map((job, index) => (
          <JobCard key={job.id} job={job} delay={Math.min(index * 0.04, 0.3)} />
        ))}
      </div>
      {nextCursor ? (
        <button
          type="button"
          onClick={loadMore}
          disabled={loading}
          className="mx-auto inline-flex h-10 items-center gap-2 rounded-lg border border-border-strong px-5 text-sm font-medium text-foreground transition-all duration-200 hover:border-primary/40 hover:bg-surface disabled:opacity-50"
        >
          {loading ? <Loader2 className="size-4 animate-spin" strokeWidth={1.75} /> : null}
          Load more
        </button>
      ) : null}
    </div>
  );
}
