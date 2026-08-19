"use client";

import { useSyncExternalStore } from "react";
import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";

// "Has the client hydrated yet?" is an external environment fact, not derived render state —
// read via useSyncExternalStore (server/hydration snapshot always false) rather than an
// effect-driven setState, so there's no hydration mismatch AND no setState-in-effect
// render cascade. Same pattern as components/three/skill-network.tsx.
function subscribe() {
  return () => {};
}
function getSnapshot() {
  return true;
}
function getServerSnapshot() {
  return false;
}

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const mounted = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const isDark = mounted && resolvedTheme === "dark";

  return (
    <button
      type="button"
      aria-label="Toggle theme"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-surface hover:text-foreground"
    >
      {isDark ? (
        <Sun className="size-4.5" strokeWidth={1.75} />
      ) : (
        <Moon className="size-4.5" strokeWidth={1.75} />
      )}
    </button>
  );
}
