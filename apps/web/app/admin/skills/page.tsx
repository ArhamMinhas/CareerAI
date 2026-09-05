import type { Metadata } from "next";
import { AdminSkillsView } from "@/components/admin/admin-skills-view";

export const metadata: Metadata = {
  title: "Admin Skills",
  robots: { index: false, follow: false },
};

export default function AdminSkillsPage() {
  return (
    <div className="px-6 py-8 lg:px-10 lg:py-10">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Skills</h1>
        <p className="text-sm text-muted-foreground">
          Manage the shared skill taxonomy and see which skills still need curated content.
        </p>
      </div>

      <div className="mt-8">
        <AdminSkillsView />
      </div>
    </div>
  );
}
