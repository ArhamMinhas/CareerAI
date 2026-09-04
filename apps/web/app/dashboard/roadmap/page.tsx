import type { Metadata } from "next";
import { RoadmapView } from "@/components/dashboard/roadmap-view";

export const metadata: Metadata = {
  title: "Learning Roadmap",
  robots: { index: false, follow: false },
};

export default function RoadmapPage() {
  return (
    <div className="px-6 py-8 lg:px-10 lg:py-10">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Learning Roadmap</h1>
        <p className="text-sm text-muted-foreground">
          A step-by-step, prerequisite-ordered sequence built from your real skill gaps — not a
          generic course list.
        </p>
      </div>

      <div className="mt-8">
        <RoadmapView />
      </div>
    </div>
  );
}
