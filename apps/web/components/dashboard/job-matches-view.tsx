"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import { RefreshCw, Sparkles, ChevronDown, MapPin } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";
import { cardHover, cn } from "@/lib/utils";
import type { JobMatch, JobMatchBreakdown } from "@/lib/types/job";

type Result =
  | { kind: "loaded"; matches: JobMatch[] }
  | { kind: "error"; message: string };

const COMPONENT_LABELS: Record<keyof JobMatchBreakdown, string> = {
  semantic_similarity: "Resume fit",
  skill_overlap: "Skill overlap",
  experience_match: "Experience",
  education_match: "Education",
  preference_match: "Preferences",
  location_match: "Location",
};

export function JobMatchesView() {
  const [result, setResult] = useState<Result | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    let active = true;
    apiFetch<JobMatch[]>("/api/v1/matches")
      .then((matches) => {
        if (active) setResult({ kind: "loaded", matches });
      })
      .catch((err) => {
        if (!active) return;
        const message = err instanceof ApiError ? err.message : "Couldn't load job matches.";
        setResult({ kind: "error", message });
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      const matches = await apiFetch<JobMatch[]>("/api/v1/jobs/match", { method: "POST" });
      setResult({ kind: "loaded", matches });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Couldn't refresh job matches.";
      setResult({ kind: "error", message });
    } finally {
      setRefreshing(false);
    }
  }

  const isLoading = result === null;
  const matches = result?.kind === "loaded" ? result.matches : [];

  return (
    <div className="flex flex-col gap-6">
      <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-sm font-medium text-foreground">Ranked matches</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Computed from your resume, skills, experience, and career goals.
            </p>
          </div>
          <button
            type="button"
            onClick={handleRefresh}
            disabled={refreshing || isLoading}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border-strong px-3 text-xs font-medium text-foreground transition-all duration-200 hover:border-primary/40 hover:bg-background disabled:opacity-50"
          >
            <RefreshCw className={cn("size-3.5", refreshing && "animate-spin")} strokeWidth={1.75} />
            Refresh matches
          </button>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {isLoading ? (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
          >
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-40 animate-pulse rounded-xl border border-border bg-surface" />
            ))}
          </motion.div>
        ) : result?.kind === "error" ? (
          <motion.div
            key="error"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className={cn(cardHover, "rounded-xl border border-danger/30 bg-surface p-6 text-center")}
          >
            <p className="text-sm text-danger">{result.message}</p>
          </motion.div>
        ) : matches.length === 0 ? (
          <motion.div
            key="empty"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className={cn(
              cardHover,
              "flex flex-col items-center gap-2 rounded-xl border border-border bg-surface px-6 py-14 text-center"
            )}
          >
            <Sparkles className="size-6 text-muted-foreground" strokeWidth={1.5} />
            <h3 className="mt-2 text-sm font-medium text-foreground">No matches yet</h3>
            <p className="max-w-[40ch] text-sm text-muted-foreground">
              Hit &quot;Refresh matches&quot; to rank open postings against your profile.
            </p>
          </motion.div>
        ) : (
          <motion.div
            key="loaded"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="grid grid-cols-1 gap-4 lg:grid-cols-2"
          >
            {matches.map((match, i) => (
              <MatchCard key={match.id} match={match} delay={Math.min(i * 0.05, 0.3)} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function MatchCard({ match, delay }: { match: JobMatch; delay: number }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link
            href={`/jobs/${match.job.id}`}
            className="text-base font-semibold tracking-tight text-foreground transition-colors hover:text-primary"
          >
            {match.job.title}
          </Link>
          <p className="mt-0.5 text-sm text-muted-foreground">{match.job.company.name}</p>
          {match.job.location || match.job.remote ? (
            <span className="mt-2 inline-flex items-center gap-1 text-xs text-muted-foreground">
              <MapPin className="size-3.5" strokeWidth={1.75} />
              {match.job.remote ? "Remote" : match.job.location}
            </span>
          ) : null}
        </div>
        <div className="flex shrink-0 flex-col items-center">
          <span className="text-2xl font-semibold tracking-tight text-foreground">
            {Math.round(match.match_score)}
            <span className="text-sm font-normal text-muted-foreground">%</span>
          </span>
          <span className="text-[11px] text-muted-foreground">match</span>
        </div>
      </div>

      <p className="mt-3 text-sm text-muted-foreground">{match.explanation}</p>

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

      <AnimatePresence>
        {expanded ? (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-3 flex flex-col gap-2 border-t border-border pt-3">
              {(Object.keys(COMPONENT_LABELS) as (keyof JobMatchBreakdown)[]).map((key) => {
                const sub = match.score_breakdown[key];
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
          </motion.div>
        ) : null}
      </AnimatePresence>
    </motion.div>
  );
}
