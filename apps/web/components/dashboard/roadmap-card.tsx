"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Map } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";
import { cardHover, cn } from "@/lib/utils";
import type { CareerGoal } from "@/lib/types/profile";
import type { CareerPath } from "@/lib/types/career-path";
import type { LearningRoadmap } from "@/lib/types/learning-roadmap";

type State = "loading" | "no-target" | "not-generated" | { roadmap: LearningRoadmap };

export function RoadmapCard() {
  const [state, setState] = useState<State>("loading");

  useEffect(() => {
    let active = true;

    async function load(): Promise<State> {
      const [careerPaths, careerGoals] = await Promise.all([
        apiFetch<CareerPath[]>("/api/v1/careers"),
        apiFetch<CareerGoal[]>("/api/v1/career-goals").catch(() => []),
      ]);
      const activeGoal = careerGoals.find((goal) => goal.is_active);
      const matched = activeGoal
        ? careerPaths.find((cp) => cp.title.toLowerCase() === activeGoal.target_role.toLowerCase())
        : undefined;
      if (!matched) return "no-target";

      try {
        const roadmap = await apiFetch<LearningRoadmap>(
          `/api/v1/learning-roadmap?target_role=${encodeURIComponent(matched.slug)}`
        );
        return { roadmap };
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return "not-generated";
        throw err;
      }
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

  const description =
    state === "loading"
      ? "Loading…"
      : state === "no-target"
        ? "Set a target role to get a personalized learning roadmap."
        : state === "not-generated"
          ? "Generate a step-by-step roadmap for your target role."
          : `${state.roadmap.progress.completed}/${state.roadmap.progress.total} steps done — tap to continue.`;

  return (
    <Link
      href="/dashboard/roadmap"
      className={cn(
        cardHover,
        "flex flex-col items-center justify-center gap-1 rounded-xl border border-border bg-surface px-6 py-10 text-center"
      )}
    >
      <Map className="size-6 text-muted-foreground" strokeWidth={1.5} />
      {typeof state === "object" ? (
        <p className="mt-4 text-2xl font-semibold tracking-tight text-foreground">
          {state.roadmap.progress.completed}
          <span className="text-sm font-normal text-muted-foreground">
            /{state.roadmap.progress.total}
          </span>
        </p>
      ) : (
        <h3 className="mt-4 text-sm font-medium text-foreground">Learning roadmap</h3>
      )}
      <p className="mt-1.5 max-w-[32ch] text-sm text-muted-foreground">{description}</p>
    </Link>
  );
}
