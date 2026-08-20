import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Shared hover treatment for card-like surfaces (bordered panels, tiles, list items) — lift,
 * border tint toward the accent, and a soft shadow. Compose with `cn(..., cardHover)` so every
 * new card built inherits the same polish by default instead of each page hand-rolling it.
 *
 * Only use this on plain (non-Motion) elements. A `motion.div` — e.g. anything wrapped in
 * `Reveal` — pins its own `transform` inline once its entrance animation settles, which
 * outranks this class's `hover:-translate-y-1` (inline styles always beat classes, so the lift
 * silently never shows). For those, use `cardHoverMotion` for the border/shadow half and
 * `Reveal`'s `hoverLift` prop for the lift, which Motion applies as `whileHover` instead.
 */
export const cardHover =
  "transition-all duration-200 ease-out hover:-translate-y-1 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5";

/** `cardHover` minus the transform-based lift — safe to pair with `Reveal`'s `hoverLift` prop. */
export const cardHoverMotion =
  "transition-[border-color,box-shadow] duration-200 ease-out hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5";
