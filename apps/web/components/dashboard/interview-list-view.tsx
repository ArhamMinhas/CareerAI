"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronDown, Loader2, MessagesSquare, Sparkles } from "lucide-react";
import { apiFetch, apiFetchWithMeta, ApiError } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cardHover, cn } from "@/lib/utils";
import {
  INTERVIEW_MODE_LABELS,
  type Interview,
  type InterviewAnalytics,
  type InterviewDetail,
  type InterviewMode,
} from "@/lib/types/interview";

const MODES = Object.keys(INTERVIEW_MODE_LABELS) as InterviewMode[];

type StartState =
  | { kind: "idle" }
  | { kind: "starting" }
  | { kind: "error"; message: string };

export function InterviewListView() {
  const router = useRouter();
  const [analytics, setAnalytics] = useState<InterviewAnalytics | null>(null);
  const [history, setHistory] = useState<Interview[] | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [mode, setMode] = useState<InterviewMode>("technical");
  const [targetRole, setTargetRole] = useState("");
  const [startState, setStartState] = useState<StartState>({ kind: "idle" });

  useEffect(() => {
    let active = true;
    Promise.all([
      apiFetch<InterviewAnalytics>("/api/v1/interviews/analytics"),
      apiFetchWithMeta<Interview[]>("/api/v1/interviews?limit=20"),
    ])
      .then(([analyticsData, historyResult]) => {
        if (!active) return;
        setAnalytics(analyticsData);
        setHistory(historyResult.data);
        setNextCursor(historyResult.meta.next_cursor);
      })
      .catch(() => {
        if (active) {
          setAnalytics(null);
          setHistory([]);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  async function loadMore() {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const result = await apiFetchWithMeta<Interview[]>(
        `/api/v1/interviews?limit=20&cursor=${encodeURIComponent(nextCursor)}`
      );
      setHistory((prev) => [...(prev ?? []), ...result.data]);
      setNextCursor(result.meta.next_cursor);
    } finally {
      setLoadingMore(false);
    }
  }

  async function handleStart() {
    if (startState.kind === "starting") return;
    setStartState({ kind: "starting" });
    try {
      const data = await apiFetch<InterviewDetail>("/api/v1/interviews", {
        method: "POST",
        body: JSON.stringify({
          mode,
          target_role: targetRole.trim() || null,
        }),
      });
      router.push(`/dashboard/interviews/${data.id}`);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Couldn't start an interview.";
      setStartState({ kind: "error", message });
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {analytics && analytics.total_completed > 0 ? (
        <AnalyticsSummary analytics={analytics} />
      ) : null}

      <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
        <h2 className="text-sm font-medium text-foreground">Start a new interview</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Pick a mode and, optionally, a target role to focus the questions toward.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <div className="relative">
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as InterviewMode)}
              className="h-10 appearance-none rounded-lg border border-border-strong bg-background pl-3.5 pr-8 text-sm font-medium text-foreground outline-none transition-colors duration-200 hover:border-primary/40"
            >
              {MODES.map((m) => (
                <option key={m} value={m}>
                  {INTERVIEW_MODE_LABELS[m]}
                </option>
              ))}
            </select>
            <ChevronDown
              className="pointer-events-none absolute right-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground"
              strokeWidth={1.75}
            />
          </div>
          <Input
            value={targetRole}
            onChange={(e) => setTargetRole(e.target.value)}
            placeholder="Target role (optional)"
            className="max-w-64"
          />
          <Button
            type="button"
            onClick={handleStart}
            disabled={startState.kind === "starting"}
            size="md"
          >
            {startState.kind === "starting" ? (
              <Loader2 className="size-4 animate-spin" strokeWidth={1.75} />
            ) : null}
            Start interview
          </Button>
        </div>
        {startState.kind === "error" ? (
          <p className="mt-3 text-xs text-danger">{startState.message}</p>
        ) : null}
      </div>

      {history === null ? (
        <div className="h-40 animate-pulse rounded-xl border border-border bg-surface" />
      ) : history.length === 0 ? (
        <div
          className={cn(
            cardHover,
            "flex flex-col items-center gap-3 rounded-xl border border-dashed border-border-strong px-6 py-16 text-center"
          )}
        >
          <MessagesSquare className="size-6 text-muted-foreground" strokeWidth={1.5} />
          <p className="max-w-[42ch] text-sm text-muted-foreground">
            No practice sessions yet — start one above to see how you do.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {history.map((interview) => (
            <HistoryRow key={interview.id} interview={interview} />
          ))}
          {nextCursor ? (
            <button
              type="button"
              onClick={loadMore}
              disabled={loadingMore}
              className="mx-auto inline-flex h-10 items-center gap-2 rounded-lg border border-border-strong px-5 text-sm font-medium text-foreground transition-all duration-200 hover:border-primary/40 hover:bg-surface disabled:opacity-50"
            >
              {loadingMore ? (
                <Loader2 className="size-4 animate-spin" strokeWidth={1.75} />
              ) : null}
              Load more
            </button>
          ) : null}
        </div>
      )}
    </div>
  );
}

function AnalyticsSummary({ analytics }: { analytics: InterviewAnalytics }) {
  return (
    <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
      <div className="flex flex-wrap items-center gap-6">
        <Stat label="Completed" value={String(analytics.total_completed)} />
        <Stat
          label="Overall"
          value={
            analytics.average_overall_score !== null
              ? Math.round(analytics.average_overall_score).toString()
              : "—"
          }
        />
        <Stat
          label="Correctness"
          value={
            analytics.average_correctness_score !== null
              ? Math.round(analytics.average_correctness_score).toString()
              : "—"
          }
        />
        <Stat
          label="Depth"
          value={
            analytics.average_depth_score !== null
              ? Math.round(analytics.average_depth_score).toString()
              : "—"
          }
        />
        <Stat
          label="Communication"
          value={
            analytics.average_communication_score !== null
              ? Math.round(analytics.average_communication_score).toString()
              : "—"
          }
        />
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xl font-semibold tracking-tight text-foreground">{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function HistoryRow({ interview }: { interview: Interview }) {
  return (
    <Link
      href={`/dashboard/interviews/${interview.id}`}
      className={cn(
        cardHover,
        "flex items-center justify-between gap-4 rounded-xl border border-border bg-surface p-4"
      )}
    >
      <div className="flex items-center gap-3">
        <Sparkles className="size-4 shrink-0 text-muted-foreground" strokeWidth={1.5} />
        <div>
          <p className="text-sm font-medium text-foreground">
            {INTERVIEW_MODE_LABELS[interview.mode]}
            {interview.target_role ? ` · ${interview.target_role}` : ""}
          </p>
          <p className="text-xs text-muted-foreground">
            {new Date(interview.created_at).toLocaleDateString()} ·{" "}
            {interview.status === "in_progress" ? "In progress" : "Completed"}
          </p>
        </div>
      </div>
      {interview.overall_score !== null ? (
        <span className="text-sm font-semibold text-foreground">
          {Math.round(interview.overall_score)}
        </span>
      ) : null}
    </Link>
  );
}
