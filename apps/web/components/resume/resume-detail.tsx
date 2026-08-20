"use client";

import { useState } from "react";
import { Download, Loader2, RotateCw, Trash2 } from "lucide-react";
import { cardHover, cn } from "@/lib/utils";
import { apiFetch, ApiError } from "@/lib/api";
import { SCORE_LABELS, type ResumeDetail, type ScoreBreakdown } from "@/lib/types/resume";

function scoreColor(score: number) {
  if (score >= 80) return "bg-success";
  if (score >= 50) return "bg-primary";
  return "bg-danger";
}

function ScoreBar({ field, sub }: { field: keyof ScoreBreakdown; sub: ScoreBreakdown[typeof field] }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-4 py-2 text-left"
      >
        <span className="text-sm text-foreground">{SCORE_LABELS[field]}</span>
        <span className="flex items-center gap-3">
          <span className="h-1.5 w-32 overflow-hidden rounded-full bg-border">
            <span
              className={cn("block h-full rounded-full transition-all duration-500", scoreColor(sub.score))}
              style={{ width: `${sub.score}%` }}
            />
          </span>
          <span className="w-10 text-right text-xs font-medium text-muted-foreground">
            {Math.round(sub.score)}
          </span>
        </span>
      </button>
      {open ? (
        <div className="mb-2 rounded-lg bg-surface px-3 py-2.5 text-xs text-muted-foreground">
          <p>{sub.explanation}</p>
          {sub.evidence.length > 0 ? (
            <ul className="mt-1.5 flex flex-wrap gap-1.5">
              {sub.evidence.map((item, i) => (
                <li
                  key={i}
                  className="rounded-full border border-border-strong px-2 py-0.5 text-foreground"
                >
                  {item}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function ResumeDetailView({
  resume,
  onDeleted,
  onReanalyzed,
}: {
  resume: ResumeDetail;
  onDeleted: () => void;
  onReanalyzed: () => void;
}) {
  const [deleting, setDeleting] = useState(false);
  const [reanalyzing, setReanalyzing] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  async function handleDelete() {
    if (!window.confirm("Delete this resume?")) return;
    setDeleting(true);
    try {
      await apiFetch<void>(`/api/v1/resumes/${resume.id}`, { method: "DELETE" });
      onDeleted();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Couldn't delete this resume.");
      setDeleting(false);
    }
  }

  async function handleReanalyze() {
    setReanalyzing(true);
    setActionError(null);
    try {
      await apiFetch<void>(`/api/v1/resumes/${resume.id}/analyze`, {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
      });
      onReanalyzed();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Couldn't start re-analysis.");
    } finally {
      setReanalyzing(false);
    }
  }

  const extraction = resume.structured_data;
  const breakdown = resume.score_breakdown;

  return (
    <div className="flex flex-col gap-6">
      <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-medium text-foreground">{resume.file_name}</h2>
            {resume.overall_score !== null ? (
              <p className="mt-1 text-3xl font-semibold tracking-tight text-foreground">
                {Math.round(resume.overall_score)}
                <span className="text-base font-normal text-muted-foreground"> / 100</span>
              </p>
            ) : (
              <p className="mt-1 text-sm text-muted-foreground">
                {resume.status === "failed"
                  ? (resume.failure_reason ?? "Analysis failed.")
                  : "Analysis in progress…"}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {resume.file_download_url ? (
              <a
                href={resume.file_download_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border-strong px-3 text-xs font-medium text-foreground transition-all duration-200 hover:border-primary/40 hover:bg-background"
              >
                <Download className="size-3.5" strokeWidth={1.75} />
                Download
              </a>
            ) : null}
            <button
              type="button"
              onClick={handleReanalyze}
              disabled={reanalyzing || resume.status === "processing"}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border-strong px-3 text-xs font-medium text-foreground transition-all duration-200 hover:border-primary/40 hover:bg-background disabled:opacity-50"
            >
              {reanalyzing ? (
                <Loader2 className="size-3.5 animate-spin" strokeWidth={1.75} />
              ) : (
                <RotateCw className="size-3.5" strokeWidth={1.75} />
              )}
              Re-analyze
            </button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="inline-flex size-9 items-center justify-center rounded-lg border border-border-strong text-muted-foreground transition-all duration-200 hover:border-danger/40 hover:text-danger disabled:opacity-50"
            >
              {deleting ? (
                <Loader2 className="size-3.5 animate-spin" strokeWidth={1.75} />
              ) : (
                <Trash2 className="size-3.5" strokeWidth={1.75} />
              )}
            </button>
          </div>
        </div>
        {actionError ? <p className="mt-3 text-sm text-danger">{actionError}</p> : null}
      </div>

      {breakdown ? (
        <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
          <h3 className="text-sm font-medium text-foreground">Score breakdown</h3>
          <p className="mt-1 text-xs text-muted-foreground">Click a row for the full explanation.</p>
          <div className="mt-4 divide-y divide-border">
            {(Object.keys(SCORE_LABELS) as (keyof ScoreBreakdown)[]).map((field) => (
              <ScoreBar key={field} field={field} sub={breakdown[field]} />
            ))}
          </div>
        </div>
      ) : null}

      {extraction ? (
        <div className={cn(cardHover, "rounded-xl border border-border bg-surface p-6")}>
          <h3 className="text-sm font-medium text-foreground">What we found</h3>
          {extraction.summary ? (
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{extraction.summary}</p>
          ) : null}

          {extraction.skills.length > 0 ? (
            <div className="mt-4">
              <p className="text-xs font-medium text-muted-foreground">Skills</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {extraction.skills.map((skill) => (
                  <span
                    key={skill}
                    className="rounded-full border border-border-strong px-2.5 py-1 text-xs text-foreground"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          {extraction.experience.length > 0 ? (
            <div className="mt-5">
              <p className="text-xs font-medium text-muted-foreground">Experience</p>
              <ul className="mt-2 flex flex-col gap-3">
                {extraction.experience.map((entry, i) => (
                  <li key={i} className="text-sm">
                    <p className="font-medium text-foreground">
                      {entry.title}
                      {entry.company ? ` · ${entry.company}` : ""}
                    </p>
                    {entry.bullets.length > 0 ? (
                      <ul className="mt-1 list-inside list-disc text-muted-foreground">
                        {entry.bullets.map((bullet, j) => (
                          <li key={j}>{bullet}</li>
                        ))}
                      </ul>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {extraction.education.length > 0 ? (
            <div className="mt-5">
              <p className="text-xs font-medium text-muted-foreground">Education</p>
              <ul className="mt-2 flex flex-col gap-1.5 text-sm">
                {extraction.education.map((entry, i) => (
                  <li key={i} className="text-foreground">
                    {entry.institution}
                    {entry.degree ? ` — ${entry.degree}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {extraction.projects.length > 0 ? (
            <div className="mt-5">
              <p className="text-xs font-medium text-muted-foreground">Projects</p>
              <ul className="mt-2 flex flex-col gap-1.5 text-sm">
                {extraction.projects.map((entry, i) => (
                  <li key={i}>
                    {entry.url ? (
                      <a
                        href={entry.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary hover:underline"
                      >
                        {entry.title}
                      </a>
                    ) : (
                      <span className="text-foreground">{entry.title}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
