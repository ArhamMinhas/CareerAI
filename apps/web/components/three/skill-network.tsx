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

/**
 * Renders the interactive 3D skill/career network on capable desktop devices, and a static
 * 2D SVG on mobile, low-end hardware, or prefers-reduced-motion — per
 * docs/UI_ARCHITECTURE.md §6.
 */
export function SkillNetwork() {
  const reduceMotion = useReducedMotion();
  const canRender3D = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  if (reduceMotion || !canRender3D) {
    return <SkillNetworkFallback />;
  }

  return <SkillNetworkScene />;
}
