"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Loader2, Plus } from "lucide-react";
import { apiFetch, apiFetchWithMeta, ApiError } from "@/lib/api";
import { Input, Textarea } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cardHover, cn } from "@/lib/utils";
import type { AdminJob, AdminJobCreateRequest } from "@/lib/types/admin";

type CreateState = { kind: "idle" } | { kind: "submitting" } | { kind: "error"; message: string };

export function AdminJobsView() {
  const [jobs, setJobs] = useState<AdminJob[] | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [createState, setCreateState] = useState<CreateState>({ kind: "idle" });

  const [companyId, setCompanyId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [skillNames, setSkillNames] = useState("");

  async function loadFirstPage() {
    const result = await apiFetchWithMeta<AdminJob[]>("/api/v1/admin/jobs?limit=20");
    setJobs(result.data);
    setNextCursor(result.meta.next_cursor);
  }

  useEffect(() => {
    loadFirstPage().catch(() => setJobs([]));
  }, []);

  async function loadMore() {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const result = await apiFetchWithMeta<AdminJob[]>(
        `/api/v1/admin/jobs?limit=20&cursor=${encodeURIComponent(nextCursor)}`
      );
      setJobs((prev) => [...(prev ?? []), ...result.data]);
      setNextCursor(result.meta.next_cursor);
    } finally {
      setLoadingMore(false);
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (createState.kind === "submitting") return;
    setCreateState({ kind: "submitting" });
    try {
      const payload: AdminJobCreateRequest = {
        company_id: companyId.trim(),
        title: title.trim(),
        description: description.trim(),
        required_skill_names: skillNames
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      };
      await apiFetch("/api/v1/admin/jobs", { method: "POST", body: JSON.stringify(payload) });
      setCompanyId("");
      setTitle("");
      setDescription("");
      setSkillNames("");
      setShowForm(false);
      setCreateState({ kind: "idle" });
      await loadFirstPage();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Couldn't create this job.";
      setCreateState({ kind: "error", message });
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <Button type="button" size="md" onClick={() => setShowForm((v) => !v)}>
          <Plus className="size-4" strokeWidth={1.75} />
          {showForm ? "Cancel" : "New job"}
        </Button>
      </div>

      {showForm ? (
        <form
          onSubmit={handleSubmit}
          className={cn(cardHover, "flex flex-col gap-3 rounded-xl border border-border bg-surface p-6")}
        >
          <Input
            value={companyId}
            onChange={(e) => setCompanyId(e.target.value)}
            placeholder="Company ID (UUID)"
            required
          />
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Job title"
            required
          />
          <Textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Job description"
            required
          />
          <Input
            value={skillNames}
            onChange={(e) => setSkillNames(e.target.value)}
            placeholder="Required skills, comma-separated (optional)"
          />
          {createState.kind === "error" ? (
            <p className="text-xs text-danger">{createState.message}</p>
          ) : null}
          <Button type="submit" size="md" disabled={createState.kind === "submitting"}>
            {createState.kind === "submitting" ? (
              <Loader2 className="size-4 animate-spin" strokeWidth={1.75} />
            ) : null}
            Create job
          </Button>
        </form>
      ) : null}

      {jobs === null ? (
        <div className="h-64 animate-pulse rounded-xl border border-border bg-surface" />
      ) : (
        <div className={cn(cardHover, "overflow-x-auto rounded-xl border border-border bg-surface")}>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs text-muted-foreground">
                <th className="px-4 py-3 font-medium">Title</th>
                <th className="px-4 py-3 font-medium">Company</th>
                <th className="px-4 py-3 font-medium">Active</th>
                <th className="px-4 py-3 font-medium">Source</th>
                <th className="px-4 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {jobs.map((job) => (
                <tr key={job.id}>
                  <td className="px-4 py-2.5 text-foreground">{job.title}</td>
                  <td className="px-4 py-2.5 text-muted-foreground">{job.company.name}</td>
                  <td className="px-4 py-2.5">
                    <span
                      className={cn(
                        "text-xs font-medium",
                        job.is_active ? "text-success" : "text-muted-foreground"
                      )}
                    >
                      {job.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-muted-foreground">{job.source ?? "admin"}</td>
                  <td className="px-4 py-2.5 text-muted-foreground">
                    {new Date(job.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {nextCursor ? (
        <button
          type="button"
          onClick={loadMore}
          disabled={loadingMore}
          className="mx-auto inline-flex h-10 items-center gap-2 rounded-lg border border-border-strong px-5 text-sm font-medium text-foreground transition-all duration-200 hover:border-primary/40 hover:bg-surface disabled:opacity-50"
        >
          {loadingMore ? <Loader2 className="size-4 animate-spin" strokeWidth={1.75} /> : null}
          Load more
        </button>
      ) : null}
    </div>
  );
}
