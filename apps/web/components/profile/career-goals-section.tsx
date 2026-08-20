"use client";

import { useState, type FormEvent } from "react";
import { Compass, Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cardHover, cn } from "@/lib/utils";
import { apiFetch, ApiError } from "@/lib/api";
import type { CareerGoal } from "@/lib/types/profile";

type FormState = {
  target_role: string;
  target_industry: string;
  target_years_experience: string;
  is_active: boolean;
};

const emptyForm: FormState = {
  target_role: "",
  target_industry: "",
  target_years_experience: "",
  is_active: true,
};

function toPayload(form: FormState) {
  return {
    target_role: form.target_role,
    target_industry: form.target_industry || null,
    target_years_experience: form.target_years_experience
      ? Number(form.target_years_experience)
      : null,
    is_active: form.is_active,
  };
}

function CareerGoalForm({
  initial,
  onCancel,
  onSaved,
}: {
  initial?: CareerGoal;
  onCancel: () => void;
  onSaved: (row: CareerGoal) => void;
}) {
  const [form, setForm] = useState<FormState>(
    initial
      ? {
          target_role: initial.target_role,
          target_industry: initial.target_industry ?? "",
          target_years_experience: initial.target_years_experience?.toString() ?? "",
          is_active: initial.is_active,
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
        ? await apiFetch<CareerGoal>(`/api/v1/career-goals/${initial.id}`, {
            method: "PATCH",
            body: JSON.stringify(toPayload(form)),
          })
        : await apiFetch<CareerGoal>("/api/v1/career-goals", {
            method: "POST",
            body: JSON.stringify(toPayload(form)),
          });
      onSaved(row);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save this goal.");
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
          <Label htmlFor="target_role">Target role</Label>
          <Input
            id="target_role"
            required
            placeholder="e.g. AI Engineer"
            value={form.target_role}
            onChange={(e) => setForm({ ...form, target_role: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="target_industry">Target industry</Label>
          <Input
            id="target_industry"
            value={form.target_industry}
            onChange={(e) => setForm({ ...form, target_industry: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="target_years_experience">
            Years of experience you&apos;re aiming for
          </Label>
          <Input
            id="target_years_experience"
            type="number"
            min={0}
            max={60}
            value={form.target_years_experience}
            onChange={(e) => setForm({ ...form, target_years_experience: e.target.value })}
          />
        </div>
        <label className="flex items-center gap-2 self-end pb-2.5 text-sm text-foreground">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            className="size-4 rounded border-border-strong accent-primary"
          />
          Currently active goal
        </label>
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

export function CareerGoalsSection({
  items,
  onChange,
}: {
  items: CareerGoal[];
  onChange: (items: CareerGoal[]) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleDelete(id: string) {
    if (!window.confirm("Remove this career goal?")) return;
    setDeletingId(id);
    try {
      await apiFetch<void>(`/api/v1/career-goals/${id}`, { method: "DELETE" });
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
        <h2 className="text-sm font-medium text-foreground">Career goals</h2>
        {!adding ? (
          <Button type="button" variant="ghost" size="md" onClick={() => setAdding(true)}>
            <Plus className="size-4" strokeWidth={1.75} />
            Add
          </Button>
        ) : null}
      </div>

      <div className="mt-3 flex flex-col gap-3">
        {adding ? (
          <CareerGoalForm
            onCancel={() => setAdding(false)}
            onSaved={(row) => {
              onChange([row, ...items]);
              setAdding(false);
            }}
          />
        ) : null}

        {items.length === 0 && !adding ? (
          <p className="rounded-xl border border-dashed border-border-strong px-6 py-8 text-center text-sm text-muted-foreground">
            No career goals set yet.
          </p>
        ) : null}

        {items.map((item) =>
          editingId === item.id ? (
            <CareerGoalForm
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
                <Compass className="mt-0.5 size-5 shrink-0 text-primary" strokeWidth={1.5} />
                <div>
                  <p className="flex items-center gap-2 text-sm font-medium text-foreground">
                    {item.target_role}
                    {item.is_active ? (
                      <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                        Active
                      </span>
                    ) : null}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {[
                      item.target_industry,
                      item.target_years_experience != null
                        ? `${item.target_years_experience} yrs experience`
                        : null,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
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
