import { FileText, Target, Briefcase, MessagesSquare } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { ButtonLink } from "@/components/ui/button";

const metrics = [
  {
    icon: FileText,
    title: "Resume score",
    description: "Upload a resume to get your first score.",
  },
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
          This is the shell. Resume analysis, skill gaps, and job matching ship in later
          phases.
        </p>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric) => (
          <EmptyState key={metric.title} {...metric} />
        ))}
      </div>

      <div className="mt-10 flex flex-col items-start gap-3 rounded-xl border border-border bg-surface p-6">
        <h2 className="text-sm font-medium text-foreground">Get started</h2>
        <p className="max-w-[52ch] text-sm text-muted-foreground">
          Resume upload and profile setup are the next things to build. For now, this
          confirms the dashboard shell, navigation, and theming all work end to end.
        </p>
        <ButtonLink href="/" variant="secondary" size="md">
          Back to home
        </ButtonLink>
      </div>
    </div>
  );
}
