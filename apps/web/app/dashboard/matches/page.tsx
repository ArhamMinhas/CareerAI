import type { Metadata } from "next";
import { JobMatchesView } from "@/components/dashboard/job-matches-view";

export const metadata: Metadata = {
  title: "Job Matches",
  robots: { index: false, follow: false },
};

export default function MatchesPage() {
  return (
    <div className="px-6 py-8 lg:px-10 lg:py-10">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Job matches</h1>
        <p className="text-sm text-muted-foreground">
          Open postings ranked against your resume, skills, experience, and career goals.
        </p>
      </div>

      <div className="mt-8">
        <JobMatchesView />
      </div>
    </div>
  );
}
