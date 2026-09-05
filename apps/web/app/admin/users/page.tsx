import type { Metadata } from "next";
import { AdminUsersView } from "@/components/admin/admin-users-view";

export const metadata: Metadata = {
  title: "Admin Users",
  robots: { index: false, follow: false },
};

export default function AdminUsersPage() {
  return (
    <div className="px-6 py-8 lg:px-10 lg:py-10">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Users</h1>
        <p className="text-sm text-muted-foreground">
          Search and manage user roles. You cannot remove your own admin access here.
        </p>
      </div>

      <div className="mt-8">
        <AdminUsersView />
      </div>
    </div>
  );
}
