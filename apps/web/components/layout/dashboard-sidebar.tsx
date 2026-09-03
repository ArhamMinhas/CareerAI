"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  User,
  FileText,
  Target,
  Compass,
  Briefcase,
  Sparkles,
  ClipboardList,
  Map,
  MessagesSquare,
  BarChart3,
  Settings,
  Bot,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { SignOutButton } from "@/components/auth/sign-out-button";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/profile", label: "Profile", icon: User },
  { href: "/dashboard/resume", label: "Resume", icon: FileText },
  { href: "/dashboard/skill-gap", label: "Skill Gap", icon: Target },
  { href: "/dashboard/ask", label: "Ask AI", icon: Bot },
  { href: "/career", label: "Career", icon: Compass },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/dashboard/matches", label: "Matches", icon: Sparkles },
  { href: "/dashboard/applications", label: "Applications", icon: ClipboardList },
  { href: "/roadmap", label: "Roadmap", icon: Map },
  { href: "/interviews", label: "Interviews", icon: MessagesSquare },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function DashboardSidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border px-3 py-6 lg:flex">
      <Link href="/" className="px-3 text-base font-semibold tracking-tight text-foreground">
        CareerAI
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

const mobileNavItems = [
  { href: "/dashboard", label: "Home", icon: LayoutDashboard },
  { href: "/dashboard/resume", label: "Resume", icon: FileText },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/dashboard/matches", label: "Matches", icon: Sparkles },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function DashboardMobileNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/95 backdrop-blur-md lg:hidden">
      <div className="grid grid-cols-5">
        {mobileNavItems.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-col items-center gap-1 py-2.5 text-[11px]",
                active ? "text-primary" : "text-muted-foreground"
              )}
            >
              <item.icon className="size-5" strokeWidth={1.75} />
              {item.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
