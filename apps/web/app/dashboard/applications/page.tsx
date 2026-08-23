import type { Metadata } from "next";
import { ApplicationsView } from "@/components/dashboard/applications-view";

export const metadata: Metadata = {
  title: "Applications",
  robots: { index: false, follow: false },
};

export default function ApplicationsPage() {
  return (
    <div className="px-6 py-8 lg:px-10 lg:py-10">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Applications</h1>
        <p className="text-sm text-muted-foreground">
          Every job you&apos;ve tracked, with its status — from saved through offer or rejected.
        </p>
      </div>

      <div className="mt-8">
        <ApplicationsView />
      </div>
    </div>
  );
}
