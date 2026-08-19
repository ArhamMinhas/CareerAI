"use client";

import { MotionConfig } from "motion/react";
import type { ReactNode } from "react";

/**
 * Centralizes prefers-reduced-motion handling instead of every component calling
 * `useReducedMotion()` and branching its own `initial` prop. That per-component pattern is
 * an SSR hydration hazard: `useReducedMotion()` can resolve differently between the server
 * render and the client's first (hydrating) render, and using it to change *which* `initial`
 * value is passed to `motion.div` changes the rendered inline style between the two passes —
 * a real hydration mismatch, not a cosmetic one.
 *
 * `reducedMotion="user"` instead keeps `initial`/`animate` values identical on both server
 * and client (so SSR output always matches), and handles the reduced-motion case by
 * collapsing the *transition* to instant at commit time — which is a client-only concern
 * Motion manages internally without touching the serialized initial state.
 */
export function MotionProvider({ children }: { children: ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
