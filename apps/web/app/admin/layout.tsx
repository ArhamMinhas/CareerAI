import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AdminNav } from "@/components/layout/admin-nav";
import type { AdminUser } from "@/lib/types/admin";

// Never indexed, same as /dashboard (docs/SEO.md §1).
export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

// Same API_INTERNAL_URL/NEXT_PUBLIC_API_URL fallback as lib/public-api.ts — this layout runs
// server-side, where a fetch from inside the web container needs the Docker-network service
// name, not the browser-facing published-port URL.
const API_BASE =
  process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default async function AdminLayout({ children }: LayoutProps<"/admin">) {
  // Two real checks, both server-side, before any admin content renders: (1) is there a
  // session at all (mirrors dashboard/layout.tsx exactly), and (2) does that session's user
  // actually have Role.ADMIN — which the Supabase JWT itself never carries (role lives solely
  // on our own `users` row), so this requires one real round trip to the already-existing
  // `GET /api/v1/auth/me`, attaching the session's access token directly (not the browser-only
  // `apiFetch` in lib/api.ts). Doing this server-side, before the page renders, avoids a
  // flash-of-admin-UI-then-redirect for a non-admin who navigates straight to /admin — the real
  // security boundary is still `require_role(Role.ADMIN)` on every actual admin API call
  // regardless; this just makes the UX honest about it up front.
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    redirect("/sign-in");
  }

  const response = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
    cache: "no-store",
  });

  if (!response.ok) {
    redirect("/sign-in");
  }

  const { data: user } = (await response.json()) as { data: AdminUser };
  if (user.role !== "ADMIN") {
    redirect("/dashboard");
  }

  return (
    <div className="flex min-h-dvh">
      <AdminNav />
      <main className="flex-1">{children}</main>
    </div>
  );
}
