import Link from "next/link";
import { BarChart3 } from "lucide-react";
import { cardHover, cn } from "@/lib/utils";

/** Deliberately minimal — this page already aggregates every other feature's own card, so a
 * duplicate mini-metric here would just be circular. A generic "view your analytics" CTA. */
export function AnalyticsCard() {
  return (
    <Link
      href="/dashboard/analytics"
      className={cn(
        cardHover,
        "flex flex-col items-center justify-center gap-1 rounded-xl border border-border bg-surface px-6 py-10 text-center"
      )}
    >
      <BarChart3 className="size-6 text-muted-foreground" strokeWidth={1.5} />
      <h3 className="mt-4 text-sm font-medium text-foreground">Analytics</h3>
      <p className="mt-1.5 max-w-[32ch] text-sm text-muted-foreground">
        Your progress across every feature, plus real market intelligence.
      </p>
    </Link>
  );
}
