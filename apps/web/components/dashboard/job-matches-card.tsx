"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Briefcase } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { cardHover, cn } from "@/lib/utils";
import type { JobMatch } from "@/lib/types/job";

type State = "loading" | "none" | { count: number; topScore: number };

export function JobMatchesCard() {
  const [state, setState] = useState<State>("loading");

  useEffect(() => {
    let active = true;
    apiFetch<JobMatch[]>("/api/v1/matches")
      .then((matches) => {
        if (!active) return;
        if (matches.length === 0) {
          setState("none");
          return;
        }
        const topScore = Math.max(...matches.map((m) => m.match_score));
        setState({ count: matches.length, topScore });
      })
      .catch(() => {
        if (active) setState("none");
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <Link
      href="/dashboard/matches"
      className={cn(
        cardHover,
        "flex flex-col items-center justify-center gap-1 rounded-xl border border-border bg-surface px-6 py-10 text-center"
      )}
    >
      <Briefcase className="size-6 text-muted-foreground" strokeWidth={1.5} />
      {typeof state === "object" ? (
        <p className="mt-4 text-2xl font-semibold tracking-tight text-foreground">
          {state.count}
          <span className="text-sm font-normal text-muted-foreground"> matches</span>
        </p>
      ) : (
        <h3 className="mt-4 text-sm font-medium text-foreground">Job matches</h3>
      )}
      <p className="mt-1.5 max-w-[32ch] text-sm text-muted-foreground">
        {state === "loading"
          ? "Loading…"
          : state === "none"
            ? "Rank open postings against your profile."
            : `Best match: ${Math.round(state.topScore)}% — tap to see them all.`}
      </p>
    </Link>
  );
}
