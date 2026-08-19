"use client";

import { useSyncExternalStore } from "react";
import dynamic from "next/dynamic";
import { useReducedMotion } from "motion/react";
import { SkillNetworkFallback } from "@/components/three/skill-network-fallback";

const SkillNetworkScene = dynamic(
  () => import("@/components/three/skill-network-scene").then((m) => m.SkillNetworkScene),
  { ssr: false }
);

function hasLowCapability(): boolean {
  const cores = navigator.hardwareConcurrency ?? 4;
  const isNarrow = window.matchMedia("(max-width: 767px)").matches;
  const conn = (navigator as { connection?: { saveData?: boolean } }).connection;
  return cores < 4 || isNarrow || Boolean(conn?.saveData);
}

// Device capability is an external environment read, not derived render state — subscribed
// via useSyncExternalStore rather than an effect-driven setState, per docs/UI_ARCHITECTURE.md
// §6. There's nothing to actually subscribe to (capability doesn't change after load), so the
// subscribe function is a no-op; getServerSnapshot always returns the fallback so the server
// and the client's first paint agree, avoiding a hydration mismatch.
function subscribe() {
  return () => {};
}
function getSnapshot() {
  return !hasLowCapability();
}
function getServerSnapshot() {
  return false;
}

const VARIANTS = {
  hero: { nodeCount: 28, radius: 3.2, cameraDistance: 7 },
  compact: { nodeCount: 14, radius: 2.4, cameraDistance: 6 },
};

/**
 * Renders the interactive 3D skill/career network on capable desktop devices — drag to
 * rotate, hover/click a node — and a static 2D SVG on mobile, low-end hardware, or
 * prefers-reduced-motion, per docs/UI_ARCHITECTURE.md §6.
 *
 * `reduceMotion` safely gates the Fallback/Scene *branch* here (unlike Hero.tsx's old bug):
 * `canRender3D` is always false at hydration time regardless of `reduceMotion`'s value (its
 * server snapshot is hardcoded false), so the OR below is already true at hydration
 * independent of `reduceMotion` — server and client agree on the first render no matter what.
 * The 3D scene only mounts on a later, post-hydration re-render, which isn't subject to the
 * hydration-match constraint.
 */
export function SkillNetwork({ variant = "hero" }: { variant?: keyof typeof VARIANTS }) {
  const reduceMotion = useReducedMotion();
  const canRender3D = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  if (reduceMotion || !canRender3D) {
    return <SkillNetworkFallback />;
  }

  return <SkillNetworkScene {...VARIANTS[variant]} />;
}
