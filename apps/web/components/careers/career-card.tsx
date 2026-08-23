import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { Reveal } from "@/components/motion/reveal";
import { cardHoverMotion, cn } from "@/lib/utils";
import type { CareerPath } from "@/lib/types/career-path";

export function CareerCard({ careerPath, delay = 0 }: { careerPath: CareerPath; delay?: number }) {
  return (
    <Reveal delay={delay} hoverLift>
      <Link
        href={`/careers/${careerPath.slug}`}
        className={cn(
          cardHoverMotion,
          "group flex h-full flex-col justify-between gap-6 rounded-xl border border-border bg-surface p-6"
        )}
      >
        <div>
          <div className="flex items-start justify-between gap-3">
            <h2 className="text-lg font-semibold tracking-tight text-foreground">
              {careerPath.title}
            </h2>
            <ArrowUpRight
              className="size-4 shrink-0 text-muted-foreground transition-all duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary"
              strokeWidth={1.75}
            />
          </div>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            {careerPath.summary}
          </p>
        </div>
        {careerPath.related_job_titles && careerPath.related_job_titles.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {careerPath.related_job_titles.slice(0, 3).map((title) => (
              <span
                key={title}
                className="rounded-full border border-border-strong px-2.5 py-1 text-xs text-muted-foreground"
              >
                {title}
              </span>
            ))}
          </div>
        ) : null}
      </Link>
    </Reveal>
  );
}
