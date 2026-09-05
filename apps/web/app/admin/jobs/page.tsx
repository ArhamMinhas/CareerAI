import type { Metadata } from "next";
import { AdminJobsView } from "@/components/admin/admin-jobs-view";

export const metadata: Metadata = {
  title: "Admin Jobs",
  robots: { index: false, follow: false },
};

export default function AdminJobsPage() {
  return (
    <div className="px-6 py-8 lg:px-10 lg:py-10">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Jobs</h1>
        <p className="text-sm text-muted-foreground">
          Manage job postings, including inactive ones. New jobs get a real embedding
          automatically.
        </p>
      </div>

      <div className="mt-8">
        <AdminJobsView />
      </div>
    </div>
  );
}
