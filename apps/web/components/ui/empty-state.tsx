import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function EmptyState({
  icon: Icon,
  title,
  description,
  className,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-border-strong px-6 py-10 text-center",
        className
      )}
    >
      <Icon className="size-6 text-muted-foreground" strokeWidth={1.5} />
      <h3 className="mt-4 text-sm font-medium text-foreground">{title}</h3>
      <p className="mt-1.5 max-w-[32ch] text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
