"use client";

import { useEffect, type ReactNode } from "react";
import Lenis from "lenis";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useReducedMotion } from "motion/react";

gsap.registerPlugin(ScrollTrigger);

/**
 * Drives Lenis smooth scroll and keeps GSAP ScrollTrigger in sync with it — the standard
 * Lenis + GSAP integration (docs/UI_ARCHITECTURE.md §5). Skipped entirely under
 * prefers-reduced-motion: native scroll behavior is the correct "reduced" state, not a
 * slowed-down version of the smooth scroll.
 */
export function SmoothScroll({ children }: { children: ReactNode }) {
  const reduce = useReducedMotion();

  useEffect(() => {
    if (reduce) return;

    const lenis = new Lenis({ autoRaf: false });
    lenis.on("scroll", ScrollTrigger.update);

    const onTick = (time: number) => lenis.raf(time * 1000);
    gsap.ticker.add(onTick);
    gsap.ticker.lagSmoothing(0);

    return () => {
      gsap.ticker.remove(onTick);
      lenis.destroy();
    };
  }, [reduce]);

  return <>{children}</>;
}
