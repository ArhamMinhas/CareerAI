import type { ComponentPropsWithoutRef } from "react";
import { cn } from "@/lib/utils";

const base =
  "flex h-10 w-full rounded-lg border border-border-strong bg-background px-3.5 text-sm text-foreground " +
  "transition-all duration-200 ease-out placeholder:text-muted-foreground " +
  "hover:border-primary/40 focus-visible:outline-none focus-visible:border-primary " +
  "focus-visible:ring-2 focus-visible:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-50 " +
  "[color-scheme:light] dark:[color-scheme:dark]";

export function Input({ className, ...props }: ComponentPropsWithoutRef<"input">) {
  return <input className={cn(base, className)} {...props} />;
}

export function Textarea({ className, ...props }: ComponentPropsWithoutRef<"textarea">) {
  return (
    <textarea
      className={cn(base, "h-auto min-h-24 resize-y py-2.5", className)}
      {...props}
    />
  );
}

export function Select({ className, ...props }: ComponentPropsWithoutRef<"select">) {
  return <select className={cn(base, "cursor-pointer", className)} {...props} />;
}
