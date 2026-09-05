"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Users, Briefcase, Tag } from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { SignOutButton } from "@/components/auth/sign-out-button";

const navItems = [
  { href: "/admin", label: "Overview", icon: LayoutDashboard },
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/jobs", label: "Jobs", icon: Briefcase },
  { href: "/admin/skills", label: "Skills", icon: Tag },
];

/** Deliberately separate from `DashboardSidebar` — `/admin` is its own, role-gated section of
 * the app, structurally distinct from `/dashboard/*` (the original route map always kept them
 * apart), with a different, much shorter nav. */
export function AdminNav() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-56 shrink-0 flex-col border-r border-border px-3 py-6 lg:flex">
      <Link href="/admin" className="px-3 text-base font-semibold tracking-tight text-foreground">
        CareerAI Admin
      </Link>

      <nav className="mt-8 flex flex-1 flex-col gap-1">
        {navItems.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-surface font-medium text-foreground"
                  : "text-muted-foreground hover:bg-surface hover:text-foreground"
              )}
            >
              <item.icon className="size-4" strokeWidth={1.75} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="flex items-center justify-between px-3">
        <SignOutButton />
        <ThemeToggle />
      </div>
    </aside>
  );
}
