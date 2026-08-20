import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { DashboardSidebar, DashboardMobileNav } from "@/components/layout/dashboard-sidebar";
import { createClient } from "@/lib/supabase/server";

// Authenticated app shell — never indexed (docs/SEO.md §1).
export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

export default async function DashboardLayout({ children }: LayoutProps<"/dashboard">) {
  // Route-level access control (proxy.ts only refreshes the session cookie, it doesn't gate
  // routes) — Phase 3, per the comment left on proxy.ts back in Phase 1. `getUser()` (not
  // `getSession()`) re-validates the token against Supabase rather than trusting the cookie
  // as-is, since this decides whether to show the authenticated shell at all.
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/sign-in");
  }

  return (
    <div className="flex min-h-dvh">
      <DashboardSidebar />
      <main className="flex-1 pb-20 lg:pb-0">{children}</main>
      <DashboardMobileNav />
    </div>
  );
}
