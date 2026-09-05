import type { Metadata } from "next";
import { AdminOverviewView } from "@/components/admin/admin-overview-view";

export const metadata: Metadata = {
  title: "Admin Overview",
  robots: { index: false, follow: false },
};

export default function AdminOverviewPage() {
  return (
    <div className="px-6 py-8 lg:px-10 lg:py-10">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Admin</h1>
        <p className="text-sm text-muted-foreground">
          System health, real AI usage, and trained model metrics.
        </p>
      </div>

      <div className="mt-8">
        <AdminOverviewView />
      </div>
    </div>
  );
}
