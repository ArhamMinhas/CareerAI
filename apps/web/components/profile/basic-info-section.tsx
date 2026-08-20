"use client";

import { useState, type FormEvent } from "react";
import { Loader2, Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cardHover, cn } from "@/lib/utils";
import { apiFetch, ApiError } from "@/lib/api";
import type { Profile } from "@/lib/types/profile";

export function BasicInfoSection({
  profile,
  onUpdated,
}: {
  profile: Profile;
  onUpdated: (profile: Profile) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    full_name: profile.full_name ?? "",
    headline: profile.headline ?? "",
    location: profile.location ?? "",
    bio: profile.bio ?? "",
  });

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await apiFetch<Profile>("/api/v1/profile", {
        method: "PATCH",
        body: JSON.stringify(form),
      });
      onUpdated(updated);
      setEditing(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save your changes.");
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    return (
      <section className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-medium text-foreground">
              {profile.full_name || "Add your name"}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {profile.headline || "No headline yet"}
              {profile.location ? ` · ${profile.location}` : ""}
            </p>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="md"
            onClick={() => setEditing(true)}
            className="shrink-0"
          >
            <Pencil className="size-4" strokeWidth={1.75} />
            Edit
          </Button>
        </div>
        {profile.bio ? (
          <p className="mt-4 max-w-[70ch] text-sm leading-relaxed text-muted-foreground">
            {profile.bio}
          </p>
        ) : null}
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-border bg-surface p-6">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="full_name">Full name</Label>
            <Input
              id="full_name"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="headline">Headline</Label>
            <Input
              id="headline"
              placeholder="e.g. Backend Engineer"
              value={form.headline}
              onChange={(e) => setForm({ ...form, headline: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="location">Location</Label>
            <Input
              id="location"
              placeholder="e.g. Toronto, Canada"
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
            />
          </div>
        </div>
        <div>
          <Label htmlFor="bio">Bio</Label>
          <Textarea
            id="bio"
            value={form.bio}
            onChange={(e) => setForm({ ...form, bio: e.target.value })}
          />
        </div>

        {error ? <p className="text-sm text-danger">{error}</p> : null}

        <div className="flex items-center gap-3">
          <Button type="submit" size="md" disabled={saving}>
            {saving ? <Loader2 className="size-4 animate-spin" strokeWidth={2} /> : null}
            Save
          </Button>
          <Button type="button" variant="ghost" size="md" onClick={() => setEditing(false)}>
            Cancel
          </Button>
        </div>
      </form>
    </section>
  );
}
