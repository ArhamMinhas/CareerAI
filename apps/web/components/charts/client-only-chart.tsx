"use client";

import { useEffect, useState, type ReactNode } from "react";

/**
 * Recharts (v3) allocates its internal SVG element ids via React's useId(), and
 * ResponsiveContainer only measures/renders its chart children once ResizeObserver is available
 * client-side — so the very first client render mounts a different number of id-consuming
 * elements than the server did. That offsets every useId() counter for everything rendered
 * after the chart, corrupting unrelated hydration elsewhere on the page (this exact bug hit the
 * homepage FAQ accordion via components/sections/market-intelligence.tsx). Deferring the real
 * chart to a post-mount render keeps the server and first-client-render trees identical (both
 * show `fallback`) — extracted here once a second Recharts consumer needed the same fix, rather
 * than copying the workaround a second time.
 */
export function ClientOnlyChart({
  children,
  fallback = null,
}: {
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) return <>{fallback}</>;
  return <>{children}</>;
}
