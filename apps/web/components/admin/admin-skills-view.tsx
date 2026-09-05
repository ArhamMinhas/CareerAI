"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Loader2, Plus } from "lucide-react";
import { apiFetch, apiFetchWithMeta, ApiError } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cardHover, cn } from "@/lib/utils";
import type { AdminSkill } from "@/lib/types/admin";

type CreateState = { kind: "idle" } | { kind: "submitting" } | { kind: "error"; message: string };

export function AdminSkillsView() {
  const [skills, setSkills] = useState<AdminSkill[] | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [createState, setCreateState] = useState<CreateState>({ kind: "idle" });

  async function loadFirstPage() {
    const result = await apiFetchWithMeta<AdminSkill[]>("/api/v1/admin/skills?limit=30");
    setSkills(result.data);
    setNextCursor(result.meta.next_cursor);
  }

  useEffect(() => {
    loadFirstPage().catch(() => setSkills([]));
  }, []);

  async function loadMore() {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const result = await apiFetchWithMeta<AdminSkill[]>(
        `/api/v1/admin/skills?limit=30&cursor=${encodeURIComponent(nextCursor)}`
      );
      setSkills((prev) => [...(prev ?? []), ...result.data]);
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
      await apiFetch("/api/v1/admin/skills", {
        method: "POST",
        body: JSON.stringify({ name: name.trim(), category: category.trim() || null }),
      });
      setName("");
      setCategory("");
      setShowForm(false);
      setCreateState({ kind: "idle" });
      await loadFirstPage();
    } catch (err) {
      const message =
        err instanceof ApiError && err.status === 409
          ? "A skill matching that name already exists."
          : err instanceof ApiError
            ? err.message
            : "Couldn't create this skill.";
      setCreateState({ kind: "error", message });
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <Button type="button" size="md" onClick={() => setShowForm((v) => !v)}>
          <Plus className="size-4" strokeWidth={1.75} />
          {showForm ? "Cancel" : "New skill"}
        </Button>
      </div>

      {showForm ? (
        <form
          onSubmit={handleSubmit}
          className={cn(
            cardHover,
            "flex flex-wrap items-start gap-3 rounded-xl border border-border bg-surface p-6"
          )}
        >
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Skill name"
            required
            className="max-w-64"
          />
          <Input
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="Category (optional)"
            className="max-w-52"
          />
          <Button type="submit" size="md" disabled={createState.kind === "submitting"}>
            {createState.kind === "submitting" ? (
              <Loader2 className="size-4 animate-spin" strokeWidth={1.75} />
            ) : null}
            Create skill
          </Button>
          {createState.kind === "error" ? (
            <p className="w-full text-xs text-danger">{createState.message}</p>
          ) : null}
        </form>
      ) : null}

      {skills === null ? (
        <div className="h-64 animate-pulse rounded-xl border border-border bg-surface" />
      ) : (
        <div className={cn(cardHover, "overflow-x-auto rounded-xl border border-border bg-surface")}>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs text-muted-foreground">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Category</th>
                <th className="px-4 py-3 font-medium">Curated content</th>
                <th className="px-4 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {skills.map((skill) => (
                <tr key={skill.id}>
                  <td className="px-4 py-2.5 text-foreground">{skill.name}</td>
                  <td className="px-4 py-2.5 text-muted-foreground">{skill.category ?? "—"}</td>
                  <td className="px-4 py-2.5">
                    <span
                      className={cn(
                        "text-xs font-medium",
                        skill.has_curated_content ? "text-success" : "text-muted-foreground"
                      )}
                    >
                      {skill.has_curated_content ? "Yes" : "No"}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-muted-foreground">
                    {new Date(skill.created_at).toLocaleDateString()}
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
