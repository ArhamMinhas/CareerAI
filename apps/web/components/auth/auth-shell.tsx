import type { ReactNode } from "react";
import Link from "next/link";

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}) {
  return (
    <div className="relative flex min-h-dvh flex-col items-center justify-center overflow-hidden px-6 py-16">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 [background:var(--gradient-ambient)]"
      />
      <Link
        href="/"
        className="relative mb-8 text-base font-semibold tracking-tight text-foreground"
      >
        CareerAI
      </Link>
      <div className="relative w-full max-w-sm rounded-xl border border-border bg-surface p-8 shadow-md">
        <h1 className="text-xl font-semibold tracking-tight text-foreground">{title}</h1>
        <p className="mt-1.5 text-sm text-muted-foreground">{subtitle}</p>
        <div className="mt-6">{children}</div>
      </div>
      <p className="relative mt-6 text-sm text-muted-foreground">{footer}</p>
    </div>
  );
}
