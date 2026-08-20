"use client";

import { useEffect, useState } from "react";
import { Loader2, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiFetch, ApiError } from "@/lib/api";
import type { ResumeDetail, ResumeSummary } from "@/lib/types/resume";
import { ResumeUpload } from "@/components/resume/resume-upload";
import { ResumeList } from "@/components/resume/resume-list";
import { ResumeDetailView } from "@/components/resume/resume-detail";

type ListState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; resumes: ResumeSummary[] };

async function fetchResumes(): Promise<ResumeSummary[]> {
  return apiFetch<ResumeSummary[]>("/api/v1/resumes");
}

export function ResumePageClient() {
  const [state, setState] = useState<ListState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ResumeDetail | null>(null);
  const [detailError, setDetailError] = useState<{ id: string; message: string } | null>(null);

  useEffect(() => {
    let active = true;
    fetchResumes()
      .then((resumes) => {
        if (!active) return;
        setState({ status: "ready", resumes });
      })
      .catch((err: unknown) => {
        if (!active) return;
        setState({
          status: "error",
          message: err instanceof ApiError ? err.message : "Couldn't load your resumes.",
        });
      });
    return () => {
      active = false;
    };
  }, [attempt]);

  const selectedSummary =
    state.status === "ready" ? state.resumes.find((r) => r.id === selectedId) : undefined;
  const selectedStatus = selectedSummary?.status;

  // Poll while anything is still processing — resumes upload asynchronously (docs/API.md),
  // so the list needs to reflect status changes without the user manually refreshing.
  useEffect(() => {
    if (state.status !== "ready") return;
    const pending = state.resumes.some((r) => r.status === "uploaded" || r.status === "processing");
    if (!pending) return;
    const timer = setTimeout(() => {
      fetchResumes()
        .then((resumes) => setState({ status: "ready", resumes }))
        .catch(() => {
          // A transient poll failure isn't worth surfacing as a page-level error — the next
          // tick tries again.
        });
    }, 3000);
    return () => clearTimeout(timer);
  }, [state]);

  // Re-runs when the summary's status flips too (e.g. processing -> completed via polling),
  // not just when a different resume is selected. No synchronous `setState` on the
  // `!selectedId` path — `detailToShow` below derives "nothing selected" from `selectedId`
  // directly instead of needing `detail` cleared out from inside the effect.
  useEffect(() => {
    if (!selectedId) return;
    const id = selectedId;
    let active = true;
    apiFetch<ResumeDetail>(`/api/v1/resumes/${id}`)
      .then((data) => {
        if (active) setDetail(data);
      })
      .catch((err: unknown) => {
        if (active) {
          setDetailError({
            id,
            message: err instanceof ApiError ? err.message : "Couldn't load this resume.",
          });
        }
      });
    return () => {
      active = false;
    };
  }, [selectedId, selectedStatus]);

  // Both gated on matching the currently selected id — guards against showing a stale,
  // previously-loaded resume's detail/error while a newly selected one is still fetching,
  // without needing to synchronously clear either from inside the effect above.
  const detailToShow = detail && detail.id === selectedId ? detail : null;
  const errorToShow = detailError && detailError.id === selectedId ? detailError.message : null;

  function handleUploaded(resume: ResumeSummary) {
    if (state.status === "ready") {
      setState({ status: "ready", resumes: [resume, ...state.resumes] });
    }
    setSelectedId(resume.id);
  }

  function handleDeleted() {
    if (state.status === "ready" && selectedId) {
      setState({ status: "ready", resumes: state.resumes.filter((r) => r.id !== selectedId) });
    }
    setSelectedId(null);
    setDetail(null);
  }

  function handleReanalyzed() {
    setAttempt((a) => a + 1);
  }

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,320px)_1fr]">
      <div className="flex flex-col gap-4">
        <ResumeUpload onUploaded={handleUploaded} />

        {state.status === "loading" ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" strokeWidth={2} />
            Loading…
          </div>
        ) : state.status === "error" ? (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border-strong px-6 py-8 text-center">
            <TriangleAlert className="size-5 text-danger" strokeWidth={1.5} />
            <p className="text-sm text-muted-foreground">{state.message}</p>
            <Button
              type="button"
              variant="secondary"
              size="md"
              onClick={() => setAttempt((a) => a + 1)}
            >
              Try again
            </Button>
          </div>
        ) : (
          <ResumeList resumes={state.resumes} selectedId={selectedId} onSelect={setSelectedId} />
        )}
      </div>

      <div>
        {!selectedId ? (
          <p className="flex h-full min-h-48 items-center justify-center rounded-xl border border-dashed border-border-strong px-6 py-16 text-center text-sm text-muted-foreground">
            Select a resume to see its score breakdown.
          </p>
        ) : errorToShow ? (
          <p className="text-sm text-danger">{errorToShow}</p>
        ) : !detailToShow ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" strokeWidth={2} />
            Loading…
          </div>
        ) : (
          <ResumeDetailView
            resume={detailToShow}
            onDeleted={handleDeleted}
            onReanalyzed={handleReanalyzed}
          />
        )}
      </div>
    </div>
  );
}
