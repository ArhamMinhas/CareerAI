import type { ComponentPropsWithoutRef } from "react";
import { cn } from "@/lib/utils";

/** Consistent section rhythm — VISUAL_DENSITY: 3, generous by default. */
export function Section({ className, ...props }: ComponentPropsWithoutRef<"section">) {
  return <section className={cn("py-24 lg:py-32", className)} {...props} />;
}
