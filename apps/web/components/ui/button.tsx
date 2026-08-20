import type { ComponentPropsWithoutRef } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";

const base =
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium " +
  "transition-all duration-200 ease-out hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98] " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 " +
  "focus-visible:ring-offset-background disabled:pointer-events-none disabled:translate-y-0 disabled:opacity-50";

const variants = {
  primary:
    "bg-primary text-primary-foreground shadow-sm hover:shadow-lg hover:shadow-primary/25 hover:opacity-90",
  secondary:
    "border border-border-strong text-foreground hover:border-primary/50 hover:bg-surface hover:shadow-md",
  ghost: "text-foreground hover:bg-surface hover:shadow-sm",
};

const sizes = {
  md: "h-10 px-5",
  lg: "h-12 px-6 text-base",
};

type ButtonOwnProps = {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
};

type ButtonProps = ButtonOwnProps & ComponentPropsWithoutRef<"button">;

export function Button({ variant = "primary", size = "md", className, ...props }: ButtonProps) {
  return (
    <button className={cn(base, variants[variant], sizes[size], className)} {...props} />
  );
}

type ButtonLinkProps = ButtonOwnProps & ComponentPropsWithoutRef<typeof Link>;

export function ButtonLink({
  variant = "primary",
  size = "md",
  className,
  ...props
}: ButtonLinkProps) {
  return <Link className={cn(base, variants[variant], sizes[size], className)} {...props} />;
}
