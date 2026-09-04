"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import Link from "next/link";
import { Loader2, Send } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";
import { Textarea } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cardHover, cn } from "@/lib/utils";
import {
  INTERVIEW_MODE_LABELS,
  type InterviewDetail,
  type InterviewQuestion,
} from "@/lib/types/interview";

const QUESTIONS_PER_INTERVIEW = 5;

type LoadState =
  | { kind: "loading" }
  | { kind: "loaded"; data: InterviewDetail }
  | { kind: "not_found" }
  | { kind: "error"; message: string };

type SubmitState =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "rate_limited"; retryAfterSeconds: number | null }
  | { kind: "error"; message: string };

export function InterviewView({ interviewId }: { interviewId: string }) {
  const [loadState, setLoadState] = useState<LoadState>({ kind: "loading" });
  const [answerText, setAnswerText] = useState("");
  const [submitState, setSubmitState] = useState<SubmitState>({ kind: "idle" });
  const [questionStartedAt, setQuestionStartedAt] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    apiFetch<InterviewDetail>(`/api/v1/interviews/${interviewId}`)
      .then((data) => {
        if (active) setLoadState({ kind: "loaded", data });
      })
      .catch((err) => {
        if (!active) return;
        if (err instanceof ApiError && err.status === 404) {
          setLoadState({ kind: "not_found" });
        } else {
          const message = err instanceof ApiError ? err.message : "Couldn't load this interview.";
          setLoadState({ kind: "error", message });
        }
      });
    return () => {
      active = false;
    };
  }, [interviewId]);

  const currentQuestion =
    loadState.kind === "loaded"
      ? loadState.data.questions.find((q) => q.answer === null)
      : undefined;

  useEffect(() => {
    if (currentQuestion) setQuestionStartedAt(Date.now());
  }, [currentQuestion?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (loadState.kind !== "loaded" || !currentQuestion) return;
    const trimmed = answerText.trim();
    if (!trimmed || submitState.kind === "submitting") return;

    const responseTimeSeconds = Math.min(
      3_600,
      Math.max(0, Math.round((Date.now() - (questionStartedAt ?? Date.now())) / 1000))
    );

    setSubmitState({ kind: "submitting" });
    try {
      const data = await apiFetch<InterviewDetail>(`/api/v1/interviews/${interviewId}/answer`, {
        method: "POST",
        body: JSON.stringify({
          question_id: currentQuestion.id,
          answer_text: trimmed,
          response_time_seconds: responseTimeSeconds,
        }),
        headers: { "Idempotency-Key": crypto.randomUUID() },
      });
      setLoadState({ kind: "loaded", data });
      setAnswerText("");
      setSubmitState({ kind: "idle" });
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setSubmitState({ kind: "rate_limited", retryAfterSeconds: err.retryAfterSeconds });
      } else {
        const message =
          err instanceof ApiError ? err.message : "Couldn't evaluate that answer. Try again.";
        setSubmitState({ kind: "error", message });
      }
    }
  }

  if (loadState.kind === "loading") {
    return <div className="h-64 animate-pulse rounded-xl border border-border bg-surface" />;
  }

  if (loadState.kind === "not_found") {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border-strong px-6 py-16 text-center">
        <p className="text-sm text-muted-foreground">
          This interview doesn&apos;t exist, or isn&apos;t yours.
        </p>
        <Link href="/dashboard/interviews" className="text-sm font-medium text-primary">
          Back to history
        </Link>
      </div>
    );
  }

  if (loadState.kind === "error") {
    return (
      <div className="rounded-xl border border-danger/30 bg-surface p-6 text-center">
        <p className="text-sm text-danger">{loadState.message}</p>
      </div>
    );
  }

  const { data } = loadState;
  const answeredCount = data.questions.filter((q) => q.answer !== null).length;

  return (
    <div className="flex flex-col gap-6">
      <SessionHeader
        mode={data.mode}
        targetRole={data.target_role}
        answeredCount={answeredCount}
      />

      <div className="flex flex-col gap-4">
        {data.questions.map((question) => (
          <QuestionCard key={question.id} question={question} />
        ))}
      </div>

      {currentQuestion ? (
        <form
          onSubmit={handleSubmit}
          className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}
        >
          <p className="text-xs font-medium text-muted-foreground">Your answer</p>
          <Textarea
            value={answerText}
            onChange={(e) => setAnswerText(e.target.value)}
            placeholder="Type your answer…"
            disabled={submitState.kind === "submitting"}
            className="mt-2 min-h-32"
            autoFocus
          />
          <div className="mt-3 flex items-center justify-between gap-4">
            <div>
              {submitState.kind === "rate_limited" ? (
                <p className="text-xs text-warning">
                  You&apos;ve submitted a lot of answers in a short window —{" "}
                  {submitState.retryAfterSeconds !== null
                    ? `try again in about ${submitState.retryAfterSeconds}s.`
                    : "please slow down and try again shortly."}
                </p>
              ) : submitState.kind === "error" ? (
                <p className="text-xs text-danger">{submitState.message}</p>
              ) : null}
            </div>
            <Button
              type="submit"
              disabled={submitState.kind === "submitting" || !answerText.trim()}
              className="shrink-0"
            >
              {submitState.kind === "submitting" ? (
                <Loader2 className="size-4 animate-spin" strokeWidth={1.75} />
              ) : (
                <Send className="size-4" strokeWidth={1.75} />
              )}
              Submit answer
            </Button>
          </div>
        </form>
      ) : data.status === "completed" ? (
        <CompletionSummary data={data} />
      ) : null}
    </div>
  );
}

function SessionHeader({
  mode,
  targetRole,
  answeredCount,
}: {
  mode: InterviewDetail["mode"];
  targetRole: string | null;
  answeredCount: number;
}) {
  const percent = Math.round((answeredCount / QUESTIONS_PER_INTERVIEW) * 100);
  return (
    <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold tracking-tight text-foreground">
          {INTERVIEW_MODE_LABELS[mode]}
          {targetRole ? ` · ${targetRole}` : ""}
        </h2>
        <span className="text-sm font-medium text-muted-foreground">
          Question {Math.min(answeredCount + 1, QUESTIONS_PER_INTERVIEW)} of{" "}
          {QUESTIONS_PER_INTERVIEW}
        </span>
      </div>
      <span className="mt-4 block h-1.5 w-full overflow-hidden rounded-full bg-border">
        <span
          className="block h-full rounded-full bg-primary transition-all duration-700"
          style={{ width: `${percent}%` }}
        />
      </span>
    </div>
  );
}

function QuestionCard({ question }: { question: InterviewQuestion }) {
  return (
    <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {question.category}
      </p>
      <p className="mt-1.5 text-sm font-medium text-foreground">{question.question_text}</p>

      {question.answer ? (
        <div className="mt-4 flex flex-col gap-3 border-t border-border pt-4">
          <p className="text-sm leading-relaxed text-muted-foreground">
            {question.answer.answer_text}
          </p>
          {question.answer.evaluation ? (
            <div className="flex flex-col gap-2">
              <div className="flex flex-wrap gap-2">
                <ScoreChip label="Correctness" value={question.answer.evaluation.correctness_score} />
                <ScoreChip label="Depth" value={question.answer.evaluation.depth_score} />
                <ScoreChip
                  label="Communication"
                  value={question.answer.evaluation.communication_score}
                />
              </div>
              <p className="text-sm leading-relaxed text-foreground">
                {question.answer.evaluation.feedback}
              </p>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function ScoreChip({ label, value }: { label: string; value: number }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border-strong px-2.5 py-1 text-xs text-muted-foreground">
      {label}
      <span className="font-semibold text-foreground">{Math.round(value)}</span>
    </span>
  );
}

function CompletionSummary({ data }: { data: InterviewDetail }) {
  return (
    <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6 text-center")}>
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Session complete
      </p>
      <p className="mt-2 text-3xl font-semibold tracking-tight text-foreground">
        {data.overall_score !== null ? Math.round(data.overall_score) : "—"}
        <span className="text-sm font-normal text-muted-foreground">/100 overall</span>
      </p>
      <Link
        href="/dashboard/interviews"
        className="mt-4 inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm transition-all duration-200 hover:opacity-90"
      >
        Back to history
      </Link>
    </div>
  );
}
