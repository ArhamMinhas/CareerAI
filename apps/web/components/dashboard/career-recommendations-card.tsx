"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Compass } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { cardHover, cn } from "@/lib/utils";
import type { CareerRecommendation } from "@/lib/types/career-path";

type State = "loading" | "none" | { top: CareerRecommendation };

export function CareerRecommendationsCard() {
  const [state, setState] = useState<State>("loading");

  useEffect(() => {
    let active = true;
    apiFetch<CareerRecommendation[]>("/api/v1/career-recommendations")
      .then((recs) => {
        if (!active) return;
        setState(recs.length === 0 ? "none" : { top: recs[0] });
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
      href={state !== "loading" && state !== "none" ? `/careers/${state.top.career_path.slug}` : "/careers"}
      className={cn(
        cardHover,
        "flex flex-col items-center justify-center gap-1 rounded-xl border border-border bg-surface px-6 py-10 text-center"
      )}
    >
      <Compass className="size-6 text-muted-foreground" strokeWidth={1.5} />
      {state !== "loading" && state !== "none" ? (
        <p className="mt-4 max-w-[26ch] text-sm font-semibold tracking-tight text-foreground">
          {state.top.career_path.title}
        </p>
      ) : (
        <h3 className="mt-4 text-sm font-medium text-foreground">Career recommendations</h3>
      )}
      <p className="mt-1.5 max-w-[32ch] text-sm text-muted-foreground">
        {state === "loading"
          ? "Loading…"
          : state === "none"
            ? "Analyze a resume to see career paths ranked for you."
            : "Your top-ranked career path — tap to see the required skills."}
      </p>
    </Link>
  );
}
