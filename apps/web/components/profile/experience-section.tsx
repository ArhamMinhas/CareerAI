"use client";

import { useState, type FormEvent } from "react";
import { Briefcase, Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cardHover, cn } from "@/lib/utils";
import { apiFetch, ApiError } from "@/lib/api";
import type { Experience } from "@/lib/types/profile";

type FormState = {
  company: string;
  title: string;
  location: string;
  employment_type: string;
  start_date: string;
  end_date: string;
  description: string;
};

const emptyForm: FormState = {
  company: "",
  title: "",
  location: "",
  employment_type: "",
  start_date: "",
  end_date: "",
  description: "",
};

function toPayload(form: FormState) {
  return {
    company: form.company,
    title: form.title,
    location: form.location || null,
    employment_type: form.employment_type || null,
    start_date: form.start_date || null,
    end_date: form.end_date || null,
    description: form.description || null,
  };
}

function ExperienceForm({
  initial,
  onCancel,
  onSaved,
}: {
  initial?: Experience;
  onCancel: () => void;
  onSaved: (row: Experience) => void;
}) {
  const [form, setForm] = useState<FormState>(
    initial
      ? {
          company: initial.company,
          title: initial.title,
          location: initial.location ?? "",
          employment_type: initial.employment_type ?? "",
          start_date: initial.start_date ?? "",
          end_date: initial.end_date ?? "",
          description: initial.description ?? "",
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
        ? await apiFetch<Experience>(`/api/v1/profile/experience/${initial.id}`, {
            method: "PATCH",
            body: JSON.stringify(toPayload(form)),
          })
        : await apiFetch<Experience>("/api/v1/profile/experience", {
            method: "POST",
            body: JSON.stringify(toPayload(form)),
          });
      onSaved(row);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save this entry.");
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
        <div>
          <Label htmlFor="company">Company</Label>
          <Input
            id="company"
            required
            value={form.company}
            onChange={(e) => setForm({ ...form, company: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="title">Title</Label>
          <Input
            id="title"
            required
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="location">Location</Label>
          <Input
            id="location"
            value={form.location}
            onChange={(e) => setForm({ ...form, location: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="employment_type">Employment type</Label>
          <Input
            id="employment_type"
            placeholder="e.g. Full-time"
            value={form.employment_type}
            onChange={(e) => setForm({ ...form, employment_type: e.target.value })}
          />
        </div>
        <div className="grid grid-cols-2 gap-4 sm:col-span-2">
          <div>
            <Label htmlFor="start_date">Start date</Label>
            <Input
              id="start_date"
              type="date"
              value={form.start_date}
              onChange={(e) => setForm({ ...form, start_date: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="end_date">End date</Label>
            <Input
              id="end_date"
              type="date"
              value={form.end_date}
              onChange={(e) => setForm({ ...form, end_date: e.target.value })}
            />
            <p className="mt-1 text-xs text-muted-foreground">Leave blank if this is current.</p>
          </div>
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

function formatRange(start: string | null, end: string | null) {
  const fmt = (d: string) => new Date(d).toLocaleDateString(undefined, { year: "numeric", month: "short" });
  if (!start && !end) return null;
  return `${start ? fmt(start) : "?"} — ${end ? fmt(end) : "Present"}`;
}

export function ExperienceSection({
  items,
  onChange,
}: {
  items: Experience[];
  onChange: (items: Experience[]) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleDelete(id: string) {
    if (!window.confirm("Remove this experience entry?")) return;
    setDeletingId(id);
    try {
      await apiFetch<void>(`/api/v1/profile/experience/${id}`, { method: "DELETE" });
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
        <h2 className="text-sm font-medium text-foreground">Experience</h2>
        {!adding ? (
          <Button type="button" variant="ghost" size="md" onClick={() => setAdding(true)}>
            <Plus className="size-4" strokeWidth={1.75} />
            Add
          </Button>
        ) : null}
      </div>

      <div className="mt-3 flex flex-col gap-3">
        {adding ? (
          <ExperienceForm
            onCancel={() => setAdding(false)}
            onSaved={(row) => {
              onChange([row, ...items]);
              setAdding(false);
            }}
          />
        ) : null}

        {items.length === 0 && !adding ? (
          <p className="rounded-xl border border-dashed border-border-strong px-6 py-8 text-center text-sm text-muted-foreground">
            No experience added yet.
          </p>
        ) : null}

        {items.map((item) =>
          editingId === item.id ? (
            <ExperienceForm
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
              <div className="flex gap-3">
                <Briefcase className="mt-0.5 size-5 shrink-0 text-primary" strokeWidth={1.5} />
                <div>
                  <p className="text-sm font-medium text-foreground">{item.title}</p>
                  <p className="text-sm text-muted-foreground">
                    {[item.company, item.location].filter(Boolean).join(" · ")}
                  </p>
                  {formatRange(item.start_date, item.end_date) ? (
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatRange(item.start_date, item.end_date)}
                    </p>
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
