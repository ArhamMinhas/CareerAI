"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ComponentProps } from "react";

/**
 * Wraps next-themes, configured to match the `data-theme` attribute strategy already built
 * into packages/config/tailwind-tokens.css (docs/UI_ARCHITECTURE.md §4). Defaults to system
 * preference, persists an explicit user choice, and next-themes handles the no-flash script
 * injection itself (`suppressHydrationWarning` on <html> in layout.tsx is required).
 */
export function ThemeProvider({ children, ...props }: ComponentProps<typeof NextThemesProvider>) {
  return (
    <NextThemesProvider
      attribute="data-theme"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
      {...props}
    >
      {children}
    </NextThemesProvider>
  );
}
