"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import Link from "next/link";
import { Loader2, Send, Sparkles } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { RagQueryResponse } from "@/lib/types/resource";

type ExchangeState =
  | { kind: "loading" }
  | { kind: "answered"; data: RagQueryResponse }
  | { kind: "rate_limited"; retryAfterSeconds: number | null }
  | { kind: "error"; message: string };

type Exchange = {
  id: string;
  question: string;
  state: ExchangeState;
};

export function AskView() {
  const [question, setQuestion] = useState("");
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || submitting) return;

    const id = crypto.randomUUID();
    setExchanges((prev) => [...prev, { id, question: trimmed, state: { kind: "loading" } }]);
    setQuestion("");
    setSubmitting(true);

    function setState(state: ExchangeState) {
      setExchanges((prev) => prev.map((ex) => (ex.id === id ? { ...ex, state } : ex)));
    }

    try {
      const data = await apiFetch<RagQueryResponse>("/api/v1/rag/query", {
        method: "POST",
        body: JSON.stringify({ question: trimmed }),
        // A fresh key per submitted question — this is a new request, not a retry of a
        // previous one, so it must not replay any earlier cached answer.
        headers: { "Idempotency-Key": id },
      });
      setState({ kind: "answered", data });
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setState({ kind: "rate_limited", retryAfterSeconds: err.retryAfterSeconds });
      } else {
        const message =
          err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
        setState({ kind: "error", message });
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <form onSubmit={handleSubmit} className="flex gap-3">
        <Input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask about resumes, skills, interviewing, negotiation…"
          disabled={submitting}
          aria-label="Ask a question"
        />
        <Button type="submit" disabled={submitting || !question.trim()} className="shrink-0">
          {submitting ? (
            <Loader2 className="size-4 animate-spin" strokeWidth={1.75} />
          ) : (
            <Send className="size-4" strokeWidth={1.75} />
          )}
          Ask
        </Button>
      </form>

      {exchanges.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border-strong px-6 py-16 text-center">
          <Sparkles className="size-6 text-muted-foreground" strokeWidth={1.5} />
          <p className="max-w-[40ch] text-sm text-muted-foreground">
            Ask a question and get an answer grounded in CareerAI&apos;s resource library, with
            citations to exactly where it came from.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {[...exchanges].reverse().map((exchange) => (
            <ExchangeCard key={exchange.id} exchange={exchange} />
          ))}
        </div>
      )}
    </div>
  );
}

function ExchangeCard({ exchange }: { exchange: Exchange }) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-6">
      <p className="text-sm font-medium text-foreground">{exchange.question}</p>
      <ExchangeAnswer state={exchange.state} />
    </div>
  );
}

function ExchangeAnswer({ state }: { state: ExchangeState }) {
  if (state.kind === "loading") {
    return (
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="size-3.5 animate-spin" strokeWidth={1.75} />
        Thinking…
      </p>
    );
  }

  if (state.kind === "rate_limited") {
    return (
      <p className="text-sm text-warning">
        You&apos;ve asked a lot of questions in a short window —{" "}
        {state.retryAfterSeconds !== null
          ? `try again in about ${state.retryAfterSeconds}s.`
          : "please slow down and try again shortly."}
      </p>
    );
  }

  if (state.kind === "error") {
    return <p className="text-sm text-danger">{state.message}</p>;
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm leading-relaxed text-muted-foreground">{state.data.answer}</p>
      {state.data.citations.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {state.data.citations.map((citation) => (
            <Link
              key={citation.resource_slug}
              href={`/resources/${citation.resource_slug}`}
              className="rounded-full border border-border-strong px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
            >
              {citation.resource_title}
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}
