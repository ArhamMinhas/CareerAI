import type { Metadata } from "next";
import { InterviewView } from "@/components/dashboard/interview-view";

export const metadata: Metadata = {
  title: "Mock Interview Session",
  robots: { index: false, follow: false },
};

export default async function InterviewSessionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <div className="px-6 py-8 lg:px-10 lg:py-10">
      <div className="mx-auto max-w-2xl">
        <InterviewView interviewId={id} />
      </div>
    </div>
  );
}
