"use client";

import type { ReactNode } from "react";
import { motion } from "motion/react";

/**
 * Fade + rise on scroll-into-view. The single reveal primitive used across every landing
 * section — one motion vocabulary, not a different animation per section (docs/UI_ARCHITECTURE.md §5).
 *
 * `initial` is a static value rather than branching on `useReducedMotion()` — that hook can
 * resolve differently between the SSR pass and the client's hydrating render, and branching
 * `initial` on it changes the rendered inline style between the two, causing a real hydration
 * mismatch. Reduced-motion handling instead comes from `MotionConfig reducedMotion="user"` in
 * components/layout/motion-provider.tsx, which collapses the transition to instant at commit
 * time without touching what gets server-rendered.
 */
export function Reveal({
  children,
  delay = 0,
  className,
  hoverLift = false,
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
  /**
   * Motion sets `transform` inline once the entrance animation settles, which permanently
   * outranks any Tailwind `hover:-translate-y-*` utility on this same element (inline styles
   * always beat classes). So the hover lift has to be expressed as a `whileHover` animation —
   * Motion composing its own transform — rather than CSS, for any card built on Reveal.
   */
  hoverLift?: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.3 }}
      whileHover={hoverLift ? { y: -4 } : undefined}
      transition={{ duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
