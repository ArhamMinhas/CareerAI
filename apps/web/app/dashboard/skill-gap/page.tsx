import type { Metadata } from "next";
import { SkillGapView } from "@/components/dashboard/skill-gap-view";

export const metadata: Metadata = {
  title: "Skill Gap",
  robots: { index: false, follow: false },
};

export default function SkillGapPage() {
  return (
    <div className="px-6 py-8 lg:px-10 lg:py-10">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Skill gap</h1>
        <p className="text-sm text-muted-foreground">
          See exactly what separates your profile from a target role, and what to learn next.
        </p>
      </div>

      <div className="mt-8">
        <SkillGapView />
      </div>
    </div>
  );
}
