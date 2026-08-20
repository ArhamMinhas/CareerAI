"use client";

import { useState, type FormEvent } from "react";
import { GraduationCap, Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cardHover, cn } from "@/lib/utils";
import { apiFetch, ApiError } from "@/lib/api";
import type { Education } from "@/lib/types/profile";

type FormState = {
  institution: string;
  degree: string;
  field_of_study: string;
  start_date: string;
  end_date: string;
  description: string;
};

const emptyForm: FormState = {
  institution: "",
  degree: "",
  field_of_study: "",
  start_date: "",
  end_date: "",
  description: "",
};

function toPayload(form: FormState) {
  return {
    institution: form.institution,
    degree: form.degree || null,
    field_of_study: form.field_of_study || null,
    start_date: form.start_date || null,
    end_date: form.end_date || null,
    description: form.description || null,
  };
}

function EducationForm({
  initial,
  onCancel,
  onSaved,
}: {
  initial?: Education;
  onCancel: () => void;
  onSaved: (row: Education) => void;
}) {
  const [form, setForm] = useState<FormState>(
    initial
      ? {
          institution: initial.institution,
          degree: initial.degree ?? "",
          field_of_study: initial.field_of_study ?? "",
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
        ? await apiFetch<Education>(`/api/v1/profile/education/${initial.id}`, {
            method: "PATCH",
            body: JSON.stringify(toPayload(form)),
          })
        : await apiFetch<Education>("/api/v1/profile/education", {
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
          <Label htmlFor="institution">Institution</Label>
          <Input
            id="institution"
            required
            value={form.institution}
            onChange={(e) => setForm({ ...form, institution: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="degree">Degree</Label>
          <Input
            id="degree"
            value={form.degree}
            onChange={(e) => setForm({ ...form, degree: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="field_of_study">Field of study</Label>
          <Input
            id="field_of_study"
            value={form.field_of_study}
            onChange={(e) => setForm({ ...form, field_of_study: e.target.value })}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
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

export function EducationSection({
  items,
  onChange,
}: {
  items: Education[];
  onChange: (items: Education[]) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleDelete(id: string) {
    if (!window.confirm("Remove this education entry?")) return;
    setDeletingId(id);
    try {
      await apiFetch<void>(`/api/v1/profile/education/${id}`, { method: "DELETE" });
      onChange(items.filter((row) => row.id !== id));
    } catch {
      // Deletion failures are rare and the item stays visible with its actions intact, so
      // the user can just try again rather than needing a dedicated error banner here.
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-foreground">Education</h2>
        {!adding ? (
          <Button type="button" variant="ghost" size="md" onClick={() => setAdding(true)}>
            <Plus className="size-4" strokeWidth={1.75} />
            Add
          </Button>
        ) : null}
      </div>

      <div className="mt-3 flex flex-col gap-3">
        {adding ? (
          <EducationForm
            onCancel={() => setAdding(false)}
            onSaved={(row) => {
              onChange([row, ...items]);
              setAdding(false);
            }}
          />
        ) : null}

        {items.length === 0 && !adding ? (
          <p className="rounded-xl border border-dashed border-border-strong px-6 py-8 text-center text-sm text-muted-foreground">
            No education added yet.
          </p>
        ) : null}

        {items.map((item) =>
          editingId === item.id ? (
            <EducationForm
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
                <GraduationCap className="mt-0.5 size-5 shrink-0 text-primary" strokeWidth={1.5} />
                <div>
                  <p className="text-sm font-medium text-foreground">{item.institution}</p>
                  <p className="text-sm text-muted-foreground">
                    {[item.degree, item.field_of_study].filter(Boolean).join(", ")}
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
