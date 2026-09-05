import type { Metadata } from "next";
import { AnalyticsView } from "@/components/dashboard/analytics-view";

export const metadata: Metadata = {
  title: "Analytics",
  robots: { index: false, follow: false },
};

export default function AnalyticsPage() {
  return (
    <div className="px-6 py-8 lg:px-10 lg:py-10">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Analytics</h1>
        <p className="text-sm text-muted-foreground">
          Your progress across resume, skills, interviews, and roadmap — plus real skill, job,
          and salary trends from the job market.
        </p>
      </div>

      <div className="mt-8">
        <AnalyticsView />
      </div>
    </div>
  );
}
