"use client";

import { useEffect, useState } from "react";
import { BookmarkPlus, Check, Loader2 } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { apiFetch, ApiError } from "@/lib/api";
import { ButtonLink, Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type AuthState = "loading" | "signed-out" | "signed-in";
type TrackState = "idle" | "saving" | "saved" | "already-saved" | "error";

export function TrackApplicationButton({ jobId }: { jobId: string }) {
  const [authState, setAuthState] = useState<AuthState>("loading");
  const [trackState, setTrackState] = useState<TrackState>("idle");

  useEffect(() => {
    const supabase = createClient();
    let active = true;
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (active) setAuthState(session ? "signed-in" : "signed-out");
    });
    return () => {
      active = false;
    };
  }, []);

  async function handleTrack() {
    setTrackState("saving");
    try {
      await apiFetch("/api/v1/applications", {
        method: "POST",
        body: JSON.stringify({ job_id: jobId }),
      });
      setTrackState("saved");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setTrackState("already-saved");
      } else {
        setTrackState("error");
      }
    }
  }

  if (authState === "loading") {
    return (
      <Button variant="secondary" size="md" className="shrink-0" disabled>
        <Loader2 className="size-4 animate-spin" strokeWidth={1.75} />
        Loading…
      </Button>
    );
  }

  if (authState === "signed-out") {
    return (
      <ButtonLink href="/sign-up" size="md" className="shrink-0">
        Sign up to track this job
      </ButtonLink>
    );
  }

  const isDone = trackState === "saved" || trackState === "already-saved";

  return (
    <Button
      variant={isDone ? "secondary" : "primary"}
      size="md"
      className={cn("shrink-0", isDone && "pointer-events-none")}
      onClick={handleTrack}
      disabled={trackState === "saving" || isDone}
    >
      {trackState === "saving" ? (
        <Loader2 className="size-4 animate-spin" strokeWidth={1.75} />
      ) : isDone ? (
        <Check className="size-4" strokeWidth={1.75} />
      ) : (
        <BookmarkPlus className="size-4" strokeWidth={1.75} />
      )}
      {trackState === "saved"
        ? "Added to your applications"
        : trackState === "already-saved"
          ? "Already tracked"
          : trackState === "error"
            ? "Couldn't save — try again"
            : "Track this application"}
    </Button>
  );
}
