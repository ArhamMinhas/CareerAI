import type { Metadata } from "next";
import { DashboardSidebar, DashboardMobileNav } from "@/components/layout/dashboard-sidebar";

// Authenticated app shell — never indexed (docs/SEO.md §1).
export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

export default function DashboardLayout({ children }: LayoutProps<"/dashboard">) {
  return (
    <div className="flex min-h-dvh">
      <DashboardSidebar />
      <main className="flex-1 pb-20 lg:pb-0">{children}</main>
      <DashboardMobileNav />
    </div>
  );
}
