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
  // Only excludes genuinely minimal hardware and small screens — this scene is a 14-28 node
  // instanced mesh plus a handful of line segments, trivially cheap for any GPU-accelerated
  // browser. Deliberately does NOT check `navigator.connection.saveData`: Data Saver is a
  // network-bandwidth preference (fewer/smaller downloads), not a rendering-capability signal
  // — conflating the two excluded users from an already-downloaded, client-side-only scene
  // for no real reason.
  const cores = navigator.hardwareConcurrency ?? 4;
  const isNarrow = window.matchMedia("(max-width: 767px)").matches;
  return cores < 2 || isNarrow;
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
 * Renders the interactive 3D skill/career network on capable, non-mobile devices — drag to
 * rotate, hover/click a node — and a static 2D SVG on mobile or low-end hardware, per
 * docs/UI_ARCHITECTURE.md §6.
 *
 * `prefers-reduced-motion` does NOT fall all the way back to the static SVG anymore. WCAG's
 * actual concern is autoplaying/unsolicited motion (parallax, auto-rotation, continuous
 * ambient movement) — not user-initiated interaction the visitor deliberately triggers by
 * dragging. So `reduceMotion` is passed into the scene instead, which turns off autoRotate
 * and the ambient per-node float/particle drift but keeps drag-to-rotate, hover, and click
 * fully working. A visitor with reduced-motion enabled still gets a real interactive scene,
 * just without anything that moves on its own.
 *
 * Only `canRender3D` gates the Fallback/Scene branch, and it's always false at hydration time
 * (server snapshot is hardcoded false) — so server and client agree on the first render
 * regardless of `reduceMotion`'s value, avoiding the hydration mismatch this bug used to cause
 * back when `reduceMotion` was part of this condition too.
 */
export function SkillNetwork({
  variant = "hero",
  skills,
}: {
  variant?: keyof typeof VARIANTS;
  /** Real skill names (e.g. the dashboard's own profile skills) — when provided, every node
   * maps 1:1 to a real skill instead of the decorative demo list, and node count follows the
   * real count rather than the variant's fixed default. */
  skills?: string[];
}) {
  const reduceMotion = useReducedMotion();
  const canRender3D = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  if (!canRender3D) {
    return <SkillNetworkFallback />;
  }

  return (
    <SkillNetworkScene {...VARIANTS[variant]} reduceMotion={Boolean(reduceMotion)} labels={skills} />
  );
}
