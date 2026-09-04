import type { Metadata } from "next";
import { InterviewListView } from "@/components/dashboard/interview-list-view";

export const metadata: Metadata = {
  title: "AI Mock Interviews",
  robots: { index: false, follow: false },
};

export default function InterviewsPage() {
  return (
    <div className="px-6 py-8 lg:px-10 lg:py-10">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          AI Mock Interviews
        </h1>
        <p className="text-sm text-muted-foreground">
          Practice real interview questions turn-by-turn, with real-time scoring and feedback on
          each answer.
        </p>
      </div>

      <div className="mt-8">
        <InterviewListView />
      </div>
    </div>
  );
}
