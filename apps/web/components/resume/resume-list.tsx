"use client";

import { CheckCircle2, CircleAlert, FileText, Loader2 } from "lucide-react";
import { cardHover, cn } from "@/lib/utils";
import type { ResumeStatus, ResumeSummary } from "@/lib/types/resume";

const STATUS_CONFIG: Record<
  ResumeStatus,
  { label: string; className: string; icon: typeof CheckCircle2 }
> = {
  uploaded: {
    label: "Queued",
    className: "text-muted-foreground bg-surface",
    icon: Loader2,
  },
  processing: {
    label: "Analyzing…",
    className: "text-primary bg-primary/10",
    icon: Loader2,
  },
  completed: {
    label: "Analyzed",
    className: "text-success bg-success/10",
    icon: CheckCircle2,
  },
  failed: {
    label: "Failed",
    className: "text-danger bg-danger/10",
    icon: CircleAlert,
  },
};

export function ResumeList({
  resumes,
  selectedId,
  onSelect,
}: {
  resumes: ResumeSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  if (resumes.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-border-strong px-6 py-8 text-center text-sm text-muted-foreground">
        No resumes uploaded yet.
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-2">
      {resumes.map((resume) => {
        const config = STATUS_CONFIG[resume.status];
        const Icon = config.icon;
        const active = resume.id === selectedId;
        return (
          <li key={resume.id}>
            <button
              type="button"
              onClick={() => onSelect(resume.id)}
              className={cn(
                cardHover,
                "flex w-full items-center justify-between gap-3 rounded-xl border p-4 text-left",
                active ? "border-primary bg-surface" : "border-border bg-background"
              )}
            >
              <div className="flex min-w-0 items-center gap-3">
                <FileText className="size-4 shrink-0 text-muted-foreground" strokeWidth={1.75} />
                <span className="truncate text-sm font-medium text-foreground">
                  {resume.file_name}
                </span>
              </div>
              <span
                className={cn(
                  "flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
                  config.className
                )}
              >
                <Icon
                  className={cn(
                    "size-3",
                    (resume.status === "processing" || resume.status === "uploaded") &&
                      "animate-spin"
                  )}
                  strokeWidth={2}
                />
                {resume.status === "completed" && resume.overall_score !== null
                  ? `${Math.round(resume.overall_score)} / 100`
                  : config.label}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
