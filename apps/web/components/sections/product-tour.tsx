import { FileText, Target, Briefcase, MessagesSquare, Map } from "lucide-react";
import { Container } from "@/components/ui/container";
import { Section } from "@/components/ui/section";
import { Reveal } from "@/components/motion/reveal";
import { cardHoverMotion, cn } from "@/lib/utils";

function ResumeScoreVisual() {
  return (
    <div className="flex h-full flex-col justify-between">
      <div>
        <FileText className="size-5 text-primary" strokeWidth={1.75} />
        <h3 className="mt-4 text-lg font-medium text-foreground">Resume intelligence</h3>
        <p className="mt-2 max-w-[36ch] text-sm text-muted-foreground">
          A transparent score across ATS compatibility, skills, experience, and structure,
          with a plain-language reason behind every point.
        </p>
      </div>
      <div className="mt-6 flex items-end gap-1.5">
        {[42, 68, 55, 81, 90].map((value, i) => (
          <div key={i} className="flex-1 rounded-t-sm bg-primary/70" style={{ height: `${value}%` }} />
        ))}
      </div>
    </div>
  );
}

function SkillGapVisual() {
  const strong = ["Python", "SQL"];
  const missing = ["RAG", "MLOps"];
  return (
    <div className="flex h-full flex-col justify-between">
      <div>
        <Target className="size-5 text-primary" strokeWidth={1.75} />
        <h3 className="mt-4 text-base font-medium text-foreground">Skill-gap analysis</h3>
      </div>
      <div className="mt-4 flex flex-wrap gap-1.5">
        {strong.map((s) => (
          <span
            key={s}
            className="rounded-full border border-border-strong px-2.5 py-1 text-xs text-foreground"
          >
            {s}
          </span>
        ))}
        {missing.map((s) => (
          <span
            key={s}
            className="rounded-full border border-dashed border-border-strong px-2.5 py-1 text-xs text-muted-foreground"
          >
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}

function JobMatchVisual() {
  return (
    <div className="flex h-full flex-col justify-between">
      <div>
        <Briefcase className="size-5 text-primary" strokeWidth={1.75} />
        <h3 className="mt-4 text-base font-medium text-foreground">Job matching</h3>
      </div>
      <div className="mt-4 space-y-2">
        {[89, 74].map((score, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-border">
              <div className="h-full rounded-full bg-primary" style={{ width: `${score}%` }} />
            </div>
            <span className="font-mono text-xs text-muted-foreground">{score}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function InterviewVisual() {
  return (
    <div className="flex h-full flex-col justify-between">
      <div>
        <MessagesSquare className="size-5 text-primary" strokeWidth={1.75} />
        <h3 className="mt-4 text-base font-medium text-foreground">AI mock interviews</h3>
      </div>
      <div className="mt-4 space-y-1.5">
        <div className="w-4/5 rounded-lg rounded-bl-sm bg-surface px-3 py-2 text-xs text-muted-foreground">
          Walk me through a time you optimized a slow query.
        </div>
        <div className="ml-auto w-3/5 rounded-lg rounded-br-sm bg-primary/10 px-3 py-2 text-xs text-foreground">
          I profiled it first, then...
        </div>
      </div>
    </div>
  );
}

function RoadmapVisual() {
  const steps = ["Python for ML", "Deep learning", "Vector databases"];
  return (
    <div className="flex h-full flex-col justify-between">
      <div>
        <Map className="size-5 text-primary" strokeWidth={1.75} />
        <h3 className="mt-4 text-base font-medium text-foreground">Learning roadmap</h3>
      </div>
      <ol className="mt-4 space-y-2.5">
        {steps.map((step, i) => (
          <li key={step} className="flex items-center gap-2.5 text-xs text-muted-foreground">
            <span
              className={cn(
                "flex size-4 shrink-0 items-center justify-center rounded-full text-[9px] font-medium",
                i === 0 ? "bg-primary text-primary-foreground" : "border border-border-strong"
              )}
            >
              {i + 1}
            </span>
            {step}
          </li>
        ))}
      </ol>
    </div>
  );
}

export function ProductTour() {
  return (
    <Section id="product">
      <Container>
        <Reveal>
          <h2 className="max-w-xl text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            Everything you need to plan your next move.
          </h2>
        </Reveal>

        <div className="mt-12 grid grid-cols-1 gap-4 md:auto-rows-55 md:grid-cols-4">
          <Reveal
            hoverLift
            className={cn(cardHoverMotion, "rounded-xl border border-border bg-surface p-6 md:col-span-2 md:row-span-2")}
          >
            <ResumeScoreVisual />
          </Reveal>
          <Reveal hoverLift delay={0.05} className={cn(cardHoverMotion, "rounded-xl border border-border bg-surface p-6 md:col-start-3")}>
            <SkillGapVisual />
          </Reveal>
          <Reveal hoverLift delay={0.1} className={cn(cardHoverMotion, "rounded-xl border border-border bg-surface p-6 md:col-start-4")}>
            <JobMatchVisual />
          </Reveal>
          <Reveal
            hoverLift
            delay={0.15}
            className={cn(cardHoverMotion, "rounded-xl border border-border bg-surface p-6 md:col-start-3 md:row-start-2")}
          >
            <InterviewVisual />
          </Reveal>
          <Reveal
            hoverLift
            delay={0.2}
            className={cn(cardHoverMotion, "rounded-xl border border-border bg-surface p-6 md:col-start-4 md:row-start-2")}
          >
            <RoadmapVisual />
          </Reveal>
        </div>
      </Container>
    </Section>
  );
}
