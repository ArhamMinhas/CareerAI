import { Target, Briefcase, MessagesSquare } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { ButtonLink } from "@/components/ui/button";
import { SkillConstellation } from "@/components/dashboard/skill-constellation";
import { ResumeScoreCard } from "@/components/resume/resume-score-card";
import { cardHover, cn } from "@/lib/utils";

const metrics = [
  {
    icon: Target,
    title: "Skill gaps",
    description: "We'll compare your skills once your profile is set up.",
  },
  {
    icon: Briefcase,
    title: "Job matches",
    description: "Matches appear here once your resume is analyzed.",
  },
  {
    icon: MessagesSquare,
    title: "Interview readiness",
    description: "Practice with an AI mock interview to see this.",
  },
];

export default function DashboardPage() {
  return (
    <div className="px-6 py-8 lg:px-10 lg:py-10">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Resume analysis is live. Skill gaps and job matching ship in later phases.
        </p>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div
          className={cn(
            cardHover,
            "overflow-hidden rounded-xl border border-border bg-surface lg:col-span-1"
          )}
        >
          <div className="h-56 w-full">
            <SkillConstellation />
          </div>
          <div className="border-t border-border px-5 py-4">
            <h2 className="text-sm font-medium text-foreground">Your skill constellation</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Drag to explore. Reflects your real skills — added manually or from an analyzed
              resume.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:col-span-2">
          <ResumeScoreCard />
          {metrics.map((metric) => (
            <EmptyState key={metric.title} {...metric} />
          ))}
        </div>
      </div>

      <div
        className={cn(
          cardHover,
          "mt-6 flex flex-col items-start gap-3 rounded-xl border border-border bg-surface p-6"
        )}
      >
        <h2 className="text-sm font-medium text-foreground">Get started</h2>
        <p className="max-w-[52ch] text-sm text-muted-foreground">
          Add your education, experience, projects, and skills — resume analysis and job
          matching will use this once those ship.
        </p>
        <ButtonLink href="/dashboard/profile" size="md">
          Complete your profile
        </ButtonLink>
      </div>
    </div>
  );
}
