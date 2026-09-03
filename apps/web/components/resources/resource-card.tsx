import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { Reveal } from "@/components/motion/reveal";
import { cardHoverMotion, cn } from "@/lib/utils";
import type { Resource } from "@/lib/types/resource";

export function ResourceCard({ resource, delay = 0 }: { resource: Resource; delay?: number }) {
  return (
    <Reveal delay={delay} hoverLift>
      <Link
        href={`/resources/${resource.slug}`}
        className={cn(
          cardHoverMotion,
          "group flex h-full flex-col justify-between gap-6 rounded-xl border border-border bg-surface p-6"
        )}
      >
        <div>
          <div className="flex items-start justify-between gap-3">
            <h2 className="text-lg font-semibold tracking-tight text-foreground">
              {resource.title}
            </h2>
            <ArrowUpRight
              className="size-4 shrink-0 text-muted-foreground transition-all duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary"
              strokeWidth={1.75}
            />
          </div>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{resource.summary}</p>
        </div>
        {resource.tags && resource.tags.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {resource.tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-border-strong px-2.5 py-1 text-xs text-muted-foreground"
              >
                {tag}
              </span>
            ))}
          </div>
        ) : null}
      </Link>
    </Reveal>
  );
}
