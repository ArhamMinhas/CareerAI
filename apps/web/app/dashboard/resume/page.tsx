import type { Metadata } from "next";
import { ResumePageClient } from "@/components/resume/resume-page-client";

export const metadata: Metadata = {
  title: "Resume",
  robots: { index: false, follow: false },
};

export default function ResumePage() {
  return (
    <div className="px-6 py-8 lg:px-10 lg:py-10">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Resume</h1>
        <p className="text-sm text-muted-foreground">
          Upload a resume for a transparent, explainable score across ATS compatibility,
          skills, experience, and more.
        </p>
      </div>

      <div className="mt-8">
        <ResumePageClient />
      </div>
    </div>
  );
}
