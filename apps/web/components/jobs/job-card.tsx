import Link from "next/link";
import { ArrowUpRight, ExternalLink, MapPin } from "lucide-react";
import { Reveal } from "@/components/motion/reveal";
import { cardHoverMotion, cn } from "@/lib/utils";
import type { Job } from "@/lib/types/job";

function formatSalary(job: Job): string | null {
  if (job.salary_min == null && job.salary_max == null) return null;
  const fmt = new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: job.currency ?? "USD",
    maximumFractionDigits: 0,
  });
  if (job.salary_min != null && job.salary_max != null) {
    return `${fmt.format(job.salary_min)} – ${fmt.format(job.salary_max)}`;
  }
  return fmt.format((job.salary_min ?? job.salary_max) as number);
}

export function JobCard({ job, delay = 0 }: { job: Job; delay?: number }) {
  const salary = formatSalary(job);
  return (
    <Reveal delay={delay} hoverLift>
      {/* Stretched-link pattern rather than nesting an <a> (the Apply link) inside another <a>
      (which browsers silently mangle): the card itself is a plain div, the title click-through
      is an absolutely-positioned Link covering the whole card, and Apply sits above it at a
      higher stacking order so it stays independently clickable. */}
      <div
        className={cn(
          cardHoverMotion,
          "group relative flex h-full flex-col justify-between gap-5 rounded-xl border border-border bg-surface p-6"
        )}
      >
        <Link
          href={`/jobs/${job.id}`}
          className="absolute inset-0 z-0 rounded-xl"
          aria-label={`${job.title} at ${job.company.name}`}
        />
        <div className="relative z-1 pointer-events-none">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold tracking-tight text-foreground">
                {job.title}
              </h2>
              <p className="mt-0.5 text-sm text-muted-foreground">{job.company.name}</p>
            </div>
            <ArrowUpRight
              className="size-4 shrink-0 text-muted-foreground transition-all duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary"
              strokeWidth={1.75}
            />
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-muted-foreground">
            {job.location || job.remote ? (
              <span className="inline-flex items-center gap-1">
                <MapPin className="size-3.5" strokeWidth={1.75} />
                {job.remote ? "Remote" : job.location}
              </span>
            ) : null}
            {job.seniority_level ? <span>{job.seniority_level}</span> : null}
            {job.employment_type ? <span>{job.employment_type}</span> : null}
          </div>
        </div>
        <div className="relative z-1 flex items-center justify-between gap-3">
          {salary ? (
            <span className="w-fit rounded-full border border-border-strong px-2.5 py-1 text-xs font-medium text-foreground">
              {salary}
            </span>
          ) : (
            <span />
          )}
          {job.apply_url ? (
            <a
              href={job.apply_url}
              target="_blank"
              rel="noopener noreferrer"
              className="pointer-events-auto inline-flex items-center gap-1 text-xs font-medium text-primary transition-colors hover:underline"
            >
              Apply
              <ExternalLink className="size-3.5" strokeWidth={1.75} />
            </a>
          ) : null}
        </div>
      </div>
    </Reveal>
  );
}
