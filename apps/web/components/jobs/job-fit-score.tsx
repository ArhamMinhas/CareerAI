"use client";

import { useEffect, useState } from "react";
import { ChevronDown, Sparkles } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { apiFetch, ApiError } from "@/lib/api";
import { ButtonLink } from "@/components/ui/button";
import { cardHoverMotion, cn } from "@/lib/utils";
import type { JobFit, JobMatchBreakdown } from "@/lib/types/job";

type AuthState = "loading" | "signed-out" | "signed-in";
type FitState = { kind: "loading" } | { kind: "loaded"; fit: JobFit } | { kind: "error"; message: string };

const COMPONENT_LABELS: Record<keyof JobMatchBreakdown, string> = {
  semantic_similarity: "Resume fit",
  skill_overlap: "Skill overlap",
  experience_match: "Experience",
  education_match: "Education",
  preference_match: "Preferences",
  location_match: "Location",
};

export function JobFitScore({ jobId }: { jobId: string }) {
  const [authState, setAuthState] = useState<AuthState>("loading");
  const [fitState, setFitState] = useState<FitState>({ kind: "loading" });
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const supabase = createClient();
    let active = true;
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (active) setAuthState(session ? "signed-in" : "signed-out");
    });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (authState !== "signed-in") return;
    let active = true;
    apiFetch<JobFit>(`/api/v1/jobs/${jobId}/match`)
      .then((fit) => {
        if (active) setFitState({ kind: "loaded", fit });
      })
      .catch((err) => {
        if (!active) return;
        const message = err instanceof ApiError ? err.message : "Couldn't compute your fit for this job.";
        setFitState({ kind: "error", message });
      });
    return () => {
      active = false;
    };
  }, [authState, jobId]);

  if (authState === "loading") return null;

  if (authState === "signed-out") {
    return (
      <div className={cn(cardHoverMotion, "rounded-xl border border-border bg-surface p-6")}>
        <div className="flex items-center gap-2">
          <Sparkles className="size-4 text-muted-foreground" strokeWidth={1.75} />
          <h2 className="text-sm font-medium text-foreground">Your fit for this role</h2>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          Sign in to see how well this posting matches your resume, skills, and career goals.
        </p>
        <ButtonLink href="/sign-up" size="md" className="mt-4">
          Sign up to see your fit
        </ButtonLink>
      </div>
    );
  }

  if (fitState.kind === "loading") {
    return <div className="h-40 animate-pulse rounded-xl border border-border bg-surface" />;
  }

  if (fitState.kind === "error") {
    return (
      <div className={cn(cardHoverMotion, "rounded-xl border border-danger/30 bg-surface p-6")}>
        <p className="text-sm text-danger">{fitState.message}</p>
      </div>
    );
  }

  const { fit } = fitState;

  return (
    <div className={cn(cardHoverMotion, "rounded-xl border border-border bg-surface p-6")}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-medium text-foreground">Your fit for this role</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Computed from your resume, skills, experience, and career goals.
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-center">
          <span className="text-2xl font-semibold tracking-tight text-foreground">
            {Math.round(fit.match_score)}
            <span className="text-sm font-normal text-muted-foreground">%</span>
          </span>
          <span className="text-[11px] text-muted-foreground">match</span>
        </div>
      </div>

      <p className="mt-3 text-sm text-muted-foreground">{fit.explanation}</p>

      {fit.ml_suitability_probability !== null ? (
        <p className="mt-2 text-xs text-muted-foreground">
          Model signal: {Math.round(fit.ml_suitability_probability * 100)}% predicted suitability
          <span className="text-muted-foreground/70"> (supplementary, not the primary score)</span>
        </p>
      ) : null}

      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="mt-4 inline-flex items-center gap-1 text-xs font-medium text-foreground transition-colors hover:text-primary"
      >
        <ChevronDown
          className={cn("size-3.5 transition-transform duration-200", expanded && "rotate-180")}
          strokeWidth={1.75}
        />
        {expanded ? "Hide breakdown" : "Show breakdown"}
      </button>

      {expanded ? (
        <div className="mt-3 flex flex-col gap-2 border-t border-border pt-3">
          {(Object.keys(COMPONENT_LABELS) as (keyof JobMatchBreakdown)[]).map((key) => {
            const sub = fit.score_breakdown[key];
            return (
              <div key={key} className="flex items-center justify-between gap-3 text-xs">
                <span className="text-muted-foreground">{COMPONENT_LABELS[key]}</span>
                <span className="flex items-center gap-2">
                  <span className="h-1.5 w-16 overflow-hidden rounded-full bg-border">
                    <span
                      className="block h-full rounded-full bg-primary"
                      style={{ width: `${Math.max(4, sub.score)}%` }}
                    />
                  </span>
                  <span className="w-8 text-right font-medium text-foreground">
                    {Math.round(sub.score)}
                  </span>
                </span>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
