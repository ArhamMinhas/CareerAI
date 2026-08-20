"use client";

import { useEffect, useState } from "react";
import { SkillNetwork } from "@/components/three/skill-network";
import { apiFetch } from "@/lib/api";
import type { UserSkill } from "@/lib/types/profile";

type State = "loading" | "empty" | "error" | { skills: string[] };

/**
 * The dashboard's "Your skill constellation" card, backed by the user's real profile skills
 * (`/api/v1/profile/skills` — populated manually per Phase 3 and automatically from resume
 * analysis per Phase 4, so this reflects whichever source added them). Falls back to the
 * decorative demo network only while loading/on error — an empty list gets its own honest
 * "no skills yet" state rather than silently showing made-up data.
 */
export function SkillConstellation() {
  const [state, setState] = useState<State>("loading");

  useEffect(() => {
    let active = true;
    apiFetch<UserSkill[]>("/api/v1/profile/skills")
      .then((skills) => {
        if (!active) return;
        setState(skills.length > 0 ? { skills: skills.map((s) => s.name) } : "empty");
      })
      .catch(() => {
        if (active) setState("error");
      });
    return () => {
      active = false;
    };
  }, []);

  if (state === "loading") {
    return <div className="size-full animate-pulse bg-surface" />;
  }

  if (state === "empty") {
    return (
      <div className="flex size-full flex-col items-center justify-center gap-2 px-6 text-center">
        <p className="text-sm text-muted-foreground">
          No skills yet — add some to your profile or upload a resume.
        </p>
      </div>
    );
  }

  if (state === "error") {
    // Non-critical widget — the decorative network is a reasonable fallback rather than a
    // scary error state for something this low-stakes.
    return <SkillNetwork variant="compact" />;
  }

  return <SkillNetwork variant="compact" skills={state.skills} />;
}
