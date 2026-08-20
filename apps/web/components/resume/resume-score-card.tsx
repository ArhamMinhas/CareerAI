"use client";

import { useEffect, useState } from "react";
import { FileText } from "lucide-react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { cardHover, cn } from "@/lib/utils";
import type { ResumeSummary } from "@/lib/types/resume";

type State = "loading" | "empty" | { score: number } | "processing";

export function ResumeScoreCard() {
  const [state, setState] = useState<State>("loading");

  useEffect(() => {
    let active = true;
    apiFetch<ResumeSummary[]>("/api/v1/resumes")
      .then((resumes) => {
        if (!active) return;
        const latest = resumes[0];
        if (!latest) {
          setState("empty");
        } else if (latest.status === "completed" && latest.overall_score !== null) {
          setState({ score: Math.round(latest.overall_score) });
        } else if (latest.status === "failed") {
          setState("empty");
        } else {
          setState("processing");
        }
      })
      .catch(() => {
        if (active) setState("empty");
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <Link
      href="/dashboard/resume"
      className={cn(
        cardHover,
        "flex flex-col items-center justify-center gap-1 rounded-xl border border-border bg-surface px-6 py-10 text-center"
      )}
    >
      <FileText className="size-6 text-muted-foreground" strokeWidth={1.5} />
      {typeof state === "object" ? (
        <p className="mt-4 text-2xl font-semibold tracking-tight text-foreground">
          {state.score}
          <span className="text-sm font-normal text-muted-foreground"> / 100</span>
        </p>
      ) : (
        <h3 className="mt-4 text-sm font-medium text-foreground">Resume score</h3>
      )}
      <p className="mt-1.5 max-w-[32ch] text-sm text-muted-foreground">
        {state === "loading"
          ? "Loading…"
          : state === "empty"
            ? "Upload a resume to get your first score."
            : state === "processing"
              ? "Analyzing your resume…"
              : "Tap to see the full breakdown."}
      </p>
    </Link>
  );
}
