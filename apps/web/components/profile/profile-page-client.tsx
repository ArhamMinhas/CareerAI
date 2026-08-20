"use client";

import { useEffect, useState } from "react";
import { Loader2, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiFetch, ApiError } from "@/lib/api";
import type {
  CareerGoal,
  Education,
  Experience,
  Profile,
  Project,
  UserSkill,
} from "@/lib/types/profile";
import { BasicInfoSection } from "@/components/profile/basic-info-section";
import { EducationSection } from "@/components/profile/education-section";
import { ExperienceSection } from "@/components/profile/experience-section";
import { ProjectsSection } from "@/components/profile/projects-section";
import { SkillsSection } from "@/components/profile/skills-section";
import { CareerGoalsSection } from "@/components/profile/career-goals-section";

type ProfileData = {
  profile: Profile;
  education: Education[];
  experience: Experience[];
  projects: Project[];
  skills: UserSkill[];
  careerGoals: CareerGoal[];
};

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | ({ status: "ready" } & ProfileData);

function ProfileSkeleton() {
  return (
    <div className="flex flex-col gap-8">
      {[180, 220, 220, 140, 160].map((height, i) => (
        <div
          key={i}
          className="animate-pulse rounded-xl border border-border bg-surface"
          style={{ height }}
        />
      ))}
    </div>
  );
}

async function fetchProfileData(): Promise<ProfileData> {
  const [profile, education, experience, projects, skills, careerGoals] = await Promise.all([
    apiFetch<Profile>("/api/v1/profile"),
    apiFetch<Education[]>("/api/v1/profile/education"),
    apiFetch<Experience[]>("/api/v1/profile/experience"),
    apiFetch<Project[]>("/api/v1/profile/projects"),
    apiFetch<UserSkill[]>("/api/v1/profile/skills"),
    apiFetch<CareerGoal[]>("/api/v1/career-goals"),
  ]);
  return { profile, education, experience, projects, skills, careerGoals };
}

export function ProfilePageClient() {
  const [state, setState] = useState<State>({ status: "loading" });
  // Bumping this re-runs the fetch effect for the "Try again" button — a retry re-triggers
  // the effect rather than calling `setState` straight from a `useEffect` body (the effect's
  // own `setState` calls only ever happen after the `await`, never synchronously within it).
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;

    fetchProfileData()
      .then((data) => {
        if (active) setState({ status: "ready", ...data });
      })
      .catch((err: unknown) => {
        if (active) {
          setState({
            status: "error",
            message: err instanceof ApiError ? err.message : "Couldn't load your profile.",
          });
        }
      });

    return () => {
      active = false;
    };
  }, [attempt]);

  if (state.status === "loading") {
    return (
      <div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" strokeWidth={2} />
          Loading your profile…
        </div>
        <div className="mt-6">
          <ProfileSkeleton />
        </div>
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border-strong px-6 py-16 text-center">
        <TriangleAlert className="size-6 text-danger" strokeWidth={1.5} />
        <p className="text-sm text-muted-foreground">{state.message}</p>
        <Button
          type="button"
          variant="secondary"
          size="md"
          onClick={() => {
            // A click handler, not an effect — setState here is a direct response to user
            // input, not the synchronous-in-effect pattern the fetch effect above avoids.
            setState({ status: "loading" });
            setAttempt((a) => a + 1);
          }}
        >
          Try again
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-10">
      <BasicInfoSection
        profile={state.profile}
        onUpdated={(profile) => setState({ ...state, profile })}
      />
      <CareerGoalsSection
        items={state.careerGoals}
        onChange={(careerGoals) => setState({ ...state, careerGoals })}
      />
      <ExperienceSection
        items={state.experience}
        onChange={(experience) => setState({ ...state, experience })}
      />
      <EducationSection
        items={state.education}
        onChange={(education) => setState({ ...state, education })}
      />
      <ProjectsSection
        items={state.projects}
        onChange={(projects) => setState({ ...state, projects })}
      />
      <SkillsSection items={state.skills} onChange={(skills) => setState({ ...state, skills })} />
    </div>
  );
}
