"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Target } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { cardHover, cn } from "@/lib/utils";
import type { CareerGoal } from "@/lib/types/profile";
import type { CareerPath, SkillGapsResponse } from "@/lib/types/career-path";

type State = "loading" | "no-target" | { role: string; missing: number; weak: number };

export function SkillGapCard() {
  const [state, setState] = useState<State>("loading");

  useEffect(() => {
    let active = true;

    async function load() {
      const [careerPaths, careerGoals] = await Promise.all([
        apiFetch<CareerPath[]>("/api/v1/careers"),
        apiFetch<CareerGoal[]>("/api/v1/career-goals").catch(() => []),
      ]);
      const activeGoal = careerGoals.find((goal) => goal.is_active);
      const matched = activeGoal
        ? careerPaths.find((cp) => cp.title.toLowerCase() === activeGoal.target_role.toLowerCase())
        : undefined;
      if (!matched) return "no-target" as const;

      const gaps = await apiFetch<SkillGapsResponse>(
        `/api/v1/skills/gaps?target_role=${encodeURIComponent(matched.slug)}`
      );
      return { role: matched.title, missing: gaps.summary.missing, weak: gaps.summary.weak };
    }

    load()
      .then((result) => {
        if (active) setState(result);
      })
      .catch(() => {
        if (active) setState("no-target");
      });
    return () => {
      active = false;
    };
  }, []);

  const gapCount = typeof state === "object" ? state.missing + state.weak : 0;

  return (
    <Link
      href="/dashboard/skill-gap"
      className={cn(
        cardHover,
        "flex flex-col items-center justify-center gap-1 rounded-xl border border-border bg-surface px-6 py-10 text-center"
      )}
    >
      <Target className="size-6 text-muted-foreground" strokeWidth={1.5} />
      {typeof state === "object" ? (
        <p className="mt-4 text-2xl font-semibold tracking-tight text-foreground">
          {gapCount}
          <span className="text-sm font-normal text-muted-foreground"> to work on</span>
        </p>
      ) : (
        <h3 className="mt-4 text-sm font-medium text-foreground">Skill gaps</h3>
      )}
      <p className="mt-1.5 max-w-[32ch] text-sm text-muted-foreground">
        {state === "loading"
          ? "Loading…"
          : state === "no-target"
            ? "Set a target role to see your skill gaps."
            : `For ${state.role} — tap for the full breakdown.`}
      </p>
    </Link>
  );
}
