"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Loader2, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { apiFetch, ApiError } from "@/lib/api";
import type { Proficiency, Skill, UserSkill } from "@/lib/types/profile";

const PROFICIENCIES: Proficiency[] = ["beginner", "intermediate", "advanced", "expert"];

function SkillAddForm({
  existing,
  onCancel,
  onAdded,
}: {
  existing: UserSkill[];
  onCancel: () => void;
  onAdded: (row: UserSkill) => void;
}) {
  const [name, setName] = useState("");
  const [proficiency, setProficiency] = useState<Proficiency>("intermediate");
  const [suggestions, setSuggestions] = useState<Skill[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    // Below the 2-char threshold, `visibleSuggestions` below hides the dropdown regardless
    // of what's in `suggestions` — no need to clear it synchronously here (that's the
    // setState-in-effect pattern the fetch effect in profile-page-client.tsx also avoids).
    if (name.trim().length < 2) return;

    debounceRef.current = setTimeout(async () => {
      try {
        const results = await apiFetch<Skill[]>(
          `/api/v1/skills?q=${encodeURIComponent(name.trim())}`
        );
        setSuggestions(results);
      } catch {
        // Autocomplete is a convenience, not required to submit — fail silently.
      }
    }, 250);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [name]);

  const visibleSuggestions = name.trim().length < 2 ? [] : suggestions;

  async function submit(skillName: string) {
    if (existing.some((s) => s.name.toLowerCase() === skillName.trim().toLowerCase())) {
      setError("That skill is already on your profile.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const row = await apiFetch<UserSkill>("/api/v1/profile/skills", {
        method: "POST",
        body: JSON.stringify({ skill_name: skillName.trim(), proficiency }),
      });
      onAdded(row);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't add that skill.");
    } finally {
      setSaving(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) return;
    void submit(name);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <Input
            autoFocus
            placeholder="e.g. Python"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-48"
          />
          {visibleSuggestions.length > 0 ? (
            <ul className="absolute z-10 mt-1 max-h-48 w-56 overflow-auto rounded-lg border border-border bg-background py-1 shadow-md">
              {visibleSuggestions.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setName(s.name);
                      setSuggestions([]);
                    }}
                    className="w-full px-3 py-1.5 text-left text-sm text-foreground transition-colors duration-150 hover:bg-surface"
                  >
                    {s.name}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        <Select
          value={proficiency}
          onChange={(e) => setProficiency(e.target.value as Proficiency)}
          className="w-40"
        >
          {PROFICIENCIES.map((p) => (
            <option key={p} value={p}>
              {p[0].toUpperCase() + p.slice(1)}
            </option>
          ))}
        </Select>
        <Button type="submit" size="md" disabled={saving || !name.trim()}>
          {saving ? <Loader2 className="size-4 animate-spin" strokeWidth={2} /> : null}
          Add
        </Button>
        <Button type="button" variant="ghost" size="md" onClick={onCancel}>
          Cancel
        </Button>
      </div>
      {error ? <p className="text-sm text-danger">{error}</p> : null}
    </form>
  );
}

function SkillChip({
  skill,
  onProficiencyChange,
  onDelete,
}: {
  skill: UserSkill;
  onProficiencyChange: (row: UserSkill) => void;
  onDelete: () => void;
}) {
  const [updating, setUpdating] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function handleProficiencyChange(value: Proficiency) {
    setUpdating(true);
    try {
      const row = await apiFetch<UserSkill>(`/api/v1/profile/skills/${skill.id}`, {
        method: "PATCH",
        body: JSON.stringify({ proficiency: value }),
      });
      onProficiencyChange(row);
    } catch {
      // Leaves the select at its previous value on failure — nothing to reconcile since we
      // never optimistically changed it.
    } finally {
      setUpdating(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      await apiFetch<void>(`/api/v1/profile/skills/${skill.id}`, { method: "DELETE" });
      onDelete();
    } catch {
      setDeleting(false);
    }
  }

  return (
    <div className="flex items-center gap-1.5 rounded-full border border-border-strong bg-surface py-1 pl-3.5 pr-1.5 transition-all duration-200 ease-out hover:border-primary/40 hover:shadow-md">
      <span className="text-sm text-foreground">{skill.name}</span>
      <select
        value={skill.proficiency}
        disabled={updating}
        onChange={(e) => handleProficiencyChange(e.target.value as Proficiency)}
        className="rounded-full bg-transparent text-xs text-muted-foreground outline-none disabled:opacity-50"
      >
        {PROFICIENCIES.map((p) => (
          <option key={p} value={p}>
            {p[0].toUpperCase() + p.slice(1)}
          </option>
        ))}
      </select>
      <button
        type="button"
        aria-label={`Remove ${skill.name}`}
        disabled={deleting}
        onClick={handleDelete}
        className="flex size-6 items-center justify-center rounded-full text-muted-foreground transition-colors duration-150 hover:bg-background hover:text-danger disabled:opacity-50"
      >
        {deleting ? (
          <Loader2 className="size-3.5 animate-spin" strokeWidth={2} />
        ) : (
          <X className="size-3.5" strokeWidth={2} />
        )}
      </button>
    </div>
  );
}

export function SkillsSection({
  items,
  onChange,
}: {
  items: UserSkill[];
  onChange: (items: UserSkill[]) => void;
}) {
  const [adding, setAdding] = useState(false);

  return (
    <section>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-foreground">Skills</h2>
        {!adding ? (
          <Button type="button" variant="ghost" size="md" onClick={() => setAdding(true)}>
            <Plus className="size-4" strokeWidth={1.75} />
            Add
          </Button>
        ) : null}
      </div>

      <div className="mt-3 flex flex-col gap-3">
        {adding ? (
          <SkillAddForm
            existing={items}
            onCancel={() => setAdding(false)}
            onAdded={(row) => {
              onChange([row, ...items]);
              setAdding(false);
            }}
          />
        ) : null}

        {items.length === 0 && !adding ? (
          <p className="rounded-xl border border-dashed border-border-strong px-6 py-8 text-center text-sm text-muted-foreground">
            No skills added yet.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {items.map((skill) => (
              <SkillChip
                key={skill.id}
                skill={skill}
                onProficiencyChange={(row) =>
                  onChange(items.map((s) => (s.id === row.id ? row : s)))
                }
                onDelete={() => onChange(items.filter((s) => s.id !== skill.id))}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
