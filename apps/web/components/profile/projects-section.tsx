"use client";

import { useState, type FormEvent } from "react";
import { ExternalLink, FolderGit2, Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cardHover, cn } from "@/lib/utils";
import { apiFetch, ApiError } from "@/lib/api";
import type { Project } from "@/lib/types/profile";

type FormState = {
  title: string;
  description: string;
  url: string;
  repo_url: string;
  start_date: string;
  end_date: string;
};

const emptyForm: FormState = {
  title: "",
  description: "",
  url: "",
  repo_url: "",
  start_date: "",
  end_date: "",
};

function toPayload(form: FormState) {
  return {
    title: form.title,
    description: form.description || null,
    url: form.url || null,
    repo_url: form.repo_url || null,
    start_date: form.start_date || null,
    end_date: form.end_date || null,
  };
}

function ProjectForm({
  initial,
  onCancel,
  onSaved,
}: {
  initial?: Project;
  onCancel: () => void;
  onSaved: (row: Project) => void;
}) {
  const [form, setForm] = useState<FormState>(
    initial
      ? {
          title: initial.title,
          description: initial.description ?? "",
          url: initial.url ?? "",
          repo_url: initial.repo_url ?? "",
          start_date: initial.start_date ?? "",
          end_date: initial.end_date ?? "",
        }
      : emptyForm
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const row = initial
        ? await apiFetch<Project>(`/api/v1/profile/projects/${initial.id}`, {
            method: "PATCH",
            body: JSON.stringify(toPayload(form)),
          })
        : await apiFetch<Project>("/api/v1/profile/projects", {
            method: "POST",
            body: JSON.stringify(toPayload(form)),
          });
      onSaved(row);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save this project.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-4 rounded-xl border border-border bg-surface p-6"
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <Label htmlFor="title">Title</Label>
          <Input
            id="title"
            required
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="url">Live URL</Label>
          <Input
            id="url"
            type="url"
            placeholder="https://…"
            value={form.url}
            onChange={(e) => setForm({ ...form, url: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="repo_url">Repository URL</Label>
          <Input
            id="repo_url"
            type="url"
            placeholder="https://github.com/…"
            value={form.repo_url}
            onChange={(e) => setForm({ ...form, repo_url: e.target.value })}
          />
        </div>
      </div>
      <div>
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
      </div>

      {error ? <p className="text-sm text-danger">{error}</p> : null}

      <div className="flex items-center gap-3">
        <Button type="submit" size="md" disabled={saving}>
          {saving ? <Loader2 className="size-4 animate-spin" strokeWidth={2} /> : null}
          Save
        </Button>
        <Button type="button" variant="ghost" size="md" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

export function ProjectsSection({
  items,
  onChange,
}: {
  items: Project[];
  onChange: (items: Project[]) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleDelete(id: string) {
    if (!window.confirm("Remove this project?")) return;
    setDeletingId(id);
    try {
      await apiFetch<void>(`/api/v1/profile/projects/${id}`, { method: "DELETE" });
      onChange(items.filter((row) => row.id !== id));
    } catch {
      // Same reasoning as EducationSection — item stays put, user can retry.
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-foreground">Projects</h2>
        {!adding ? (
          <Button type="button" variant="ghost" size="md" onClick={() => setAdding(true)}>
            <Plus className="size-4" strokeWidth={1.75} />
            Add
          </Button>
        ) : null}
      </div>

      <div className="mt-3 flex flex-col gap-3">
        {adding ? (
          <ProjectForm
            onCancel={() => setAdding(false)}
            onSaved={(row) => {
              onChange([row, ...items]);
              setAdding(false);
            }}
          />
        ) : null}

        {items.length === 0 && !adding ? (
          <p className="rounded-xl border border-dashed border-border-strong px-6 py-8 text-center text-sm text-muted-foreground">
            No projects added yet.
          </p>
        ) : null}

        {items.map((item) =>
          editingId === item.id ? (
            <ProjectForm
              key={item.id}
              initial={item}
              onCancel={() => setEditingId(null)}
              onSaved={(row) => {
                onChange(items.map((r) => (r.id === row.id ? row : r)));
                setEditingId(null);
              }}
            />
          ) : (
            <div
              key={item.id}
              className={cn(
                cardHover,
                "flex items-start justify-between gap-4 rounded-xl border border-border bg-surface p-5"
              )}
            >
              <div>
                <p className="text-sm font-medium text-foreground">{item.title}</p>
                {item.description ? (
                  <p className="mt-1 max-w-[60ch] text-sm text-muted-foreground">
                    {item.description}
                  </p>
                ) : null}
                <div className="mt-2 flex items-center gap-3">
                  {item.url ? (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                    >
                      <ExternalLink className="size-3" strokeWidth={2} />
                      Live
                    </a>
                  ) : null}
                  {item.repo_url ? (
                    <a
                      href={item.repo_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                    >
                      <FolderGit2 className="size-3" strokeWidth={2} />
                      Code
                    </a>
                  ) : null}
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                <button
                  type="button"
                  aria-label="Edit"
                  onClick={() => setEditingId(item.id)}
                  className="flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors duration-200 hover:bg-background hover:text-foreground"
                >
                  <Pencil className="size-4" strokeWidth={1.75} />
                </button>
                <button
                  type="button"
                  aria-label="Delete"
                  disabled={deletingId === item.id}
                  onClick={() => handleDelete(item.id)}
                  className="flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors duration-200 hover:bg-background hover:text-danger disabled:opacity-50"
                >
                  {deletingId === item.id ? (
                    <Loader2 className="size-4 animate-spin" strokeWidth={1.75} />
                  ) : (
                    <Trash2 className="size-4" strokeWidth={1.75} />
                  )}
                </button>
              </div>
            </div>
          )
        )}
      </div>
    </section>
  );
}
