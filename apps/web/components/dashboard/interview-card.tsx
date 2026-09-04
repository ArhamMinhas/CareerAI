"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { MessagesSquare } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { cardHover, cn } from "@/lib/utils";
import type { InterviewAnalytics } from "@/lib/types/interview";

type State = "loading" | "error" | { analytics: InterviewAnalytics };

export function InterviewCard() {
  const [state, setState] = useState<State>("loading");

  useEffect(() => {
    let active = true;
    apiFetch<InterviewAnalytics>("/api/v1/interviews/analytics")
      .then((analytics) => {
        if (active) setState({ analytics });
      })
      .catch(() => {
        if (active) setState("error");
      });
    return () => {
      active = false;
    };
  }, []);

  const hasScore = typeof state === "object" && state.analytics.average_overall_score !== null;
  const description =
    state === "loading"
      ? "Loading…"
      : state === "error" || state.analytics.total_completed === 0
        ? "Practice with an AI mock interview to see this."
        : `${state.analytics.total_completed} session${state.analytics.total_completed === 1 ? "" : "s"} completed — tap to practice more.`;

  return (
    <Link
      href="/dashboard/interviews"
      className={cn(
        cardHover,
        "flex flex-col items-center justify-center gap-1 rounded-xl border border-border bg-surface px-6 py-10 text-center"
      )}
    >
      <MessagesSquare className="size-6 text-muted-foreground" strokeWidth={1.5} />
      {hasScore && typeof state === "object" ? (
        <p className="mt-4 text-2xl font-semibold tracking-tight text-foreground">
          {Math.round(state.analytics.average_overall_score as number)}
          <span className="text-sm font-normal text-muted-foreground">/100 avg</span>
        </p>
      ) : (
        <h3 className="mt-4 text-sm font-medium text-foreground">Interview readiness</h3>
      )}
      <p className="mt-1.5 max-w-[32ch] text-sm text-muted-foreground">{description}</p>
    </Link>
  );
}
