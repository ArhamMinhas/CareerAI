import type { Metadata } from "next";
import { AskView } from "@/components/dashboard/ask-view";

export const metadata: Metadata = {
  title: "Ask AI",
  robots: { index: false, follow: false },
};

export default function AskPage() {
  return (
    <div className="px-6 py-8 lg:px-10 lg:py-10">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Ask AI</h1>
        <p className="text-sm text-muted-foreground">
          Ask a question and get a grounded answer, cited to CareerAI&apos;s resource library —
          not a generic chatbot guess.
        </p>
      </div>

      <div className="mt-8 max-w-2xl">
        <AskView />
      </div>
    </div>
  );
}
