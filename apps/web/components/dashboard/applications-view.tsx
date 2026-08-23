"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import { Trash2, Briefcase, ChevronDown } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";
import { cardHover, cn } from "@/lib/utils";
import type { Application, ApplicationsResponse, ApplicationStatus } from "@/lib/types/job";

const STATUS_META: Record<ApplicationStatus, { label: string; dot: string }> = {
  saved: { label: "Saved", dot: "bg-muted-foreground" },
  applied: { label: "Applied", dot: "bg-primary" },
  interviewing: { label: "Interviewing", dot: "bg-warning" },
  offer: { label: "Offer", dot: "bg-success" },
  rejected: { label: "Rejected", dot: "bg-danger" },
};

const STATUS_ORDER: ApplicationStatus[] = [
  "saved",
  "applied",
  "interviewing",
  "offer",
  "rejected",
];

type Result = { kind: "loaded"; applications: Application[] } | { kind: "error"; message: string };

export function ApplicationsView() {
  const [result, setResult] = useState<Result | null>(null);

  useEffect(() => {
    let active = true;
    apiFetch<ApplicationsResponse>("/api/v1/applications")
      .then((data) => {
        if (active) setResult({ kind: "loaded", applications: data.applications });
      })
      .catch((err) => {
        if (!active) return;
        const message = err instanceof ApiError ? err.message : "Couldn't load applications.";
        setResult({ kind: "error", message });
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleStatusChange(id: string, status: ApplicationStatus) {
    if (result?.kind !== "loaded") return;
    const previous = result.applications;
    setResult({
      kind: "loaded",
      applications: previous.map((a) => (a.id === id ? { ...a, status } : a)),
    });
    try {
      await apiFetch(`/api/v1/applications/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
    } catch {
      setResult({ kind: "loaded", applications: previous });
    }
  }

  async function handleDelete(id: string) {
    if (result?.kind !== "loaded") return;
    const previous = result.applications;
    setResult({ kind: "loaded", applications: previous.filter((a) => a.id !== id) });
    try {
      await apiFetch(`/api/v1/applications/${id}`, { method: "DELETE" });
    } catch {
      setResult({ kind: "loaded", applications: previous });
    }
  }

  if (result === null) {
    return (
      <div className="flex flex-col gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded-xl border border-border bg-surface" />
        ))}
      </div>
    );
  }

  if (result.kind === "error") {
    return (
      <div className={cn(cardHover, "rounded-xl border border-danger/30 bg-surface p-6 text-center")}>
        <p className="text-sm text-danger">{result.message}</p>
      </div>
    );
  }

  if (result.applications.length === 0) {
    return (
      <div
        className={cn(
          cardHover,
          "flex flex-col items-center gap-2 rounded-xl border border-border bg-surface px-6 py-14 text-center"
        )}
      >
        <Briefcase className="size-6 text-muted-foreground" strokeWidth={1.5} />
        <h3 className="mt-2 text-sm font-medium text-foreground">Nothing tracked yet</h3>
        <p className="max-w-[40ch] text-sm text-muted-foreground">
          Track a job from its posting page, or from your ranked matches, to see it here.
        </p>
        <Link
          href="/jobs"
          className="mt-2 text-sm font-medium text-primary transition-colors hover:opacity-80"
        >
          Browse jobs →
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <AnimatePresence initial={false}>
        {result.applications.map((application) => (
          <motion.div
            key={application.id}
            layout
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, x: -8 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className={cn(
              cardHover,
              "flex flex-col items-start justify-between gap-3 rounded-xl border border-border bg-surface p-5 sm:flex-row sm:items-center"
            )}
          >
            <div>
              <Link
                href={`/jobs/${application.job.id}`}
                className="text-sm font-semibold text-foreground transition-colors hover:text-primary"
              >
                {application.job.title}
              </Link>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {application.job.company.name}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <StatusSelect
                value={application.status}
                onChange={(status) => handleStatusChange(application.id, status)}
              />
              <button
                type="button"
                onClick={() => handleDelete(application.id)}
                aria-label="Stop tracking this application"
                className="inline-flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors duration-200 hover:bg-danger/10 hover:text-danger"
              >
                <Trash2 className="size-4" strokeWidth={1.75} />
              </button>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

function StatusSelect({
  value,
  onChange,
}: {
  value: ApplicationStatus;
  onChange: (status: ApplicationStatus) => void;
}) {
  const meta = STATUS_META[value];
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as ApplicationStatus)}
        className="h-9 appearance-none rounded-lg border border-border-strong bg-background py-0 pl-7 pr-8 text-xs font-medium text-foreground outline-none transition-colors duration-200 hover:border-primary/40"
      >
        {STATUS_ORDER.map((status) => (
          <option key={status} value={status}>
            {STATUS_META[status].label}
          </option>
        ))}
      </select>
      <span
        className={cn("pointer-events-none absolute left-2.5 top-1/2 size-1.5 -translate-y-1/2 rounded-full", meta.dot)}
      />
      <ChevronDown
        className="pointer-events-none absolute right-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground"
        strokeWidth={1.75}
      />
    </div>
  );
}
