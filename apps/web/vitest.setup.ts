import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});

// jsdom implements neither API — needed by next-themes/motion (matchMedia) and
// Radix/Recharts (ResizeObserver). Standard polyfills, not test-specific hacks.
window.matchMedia =
  window.matchMedia ||
  (((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia);

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = window.ResizeObserver || (ResizeObserverStub as typeof ResizeObserver);

// Used by Motion's `whileInView` (components/motion/reveal.tsx).
class IntersectionObserverStub {
  readonly root = null;
  readonly rootMargin = "";
  readonly thresholds: ReadonlyArray<number> = [];
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
}
window.IntersectionObserver =
  window.IntersectionObserver || (IntersectionObserverStub as unknown as typeof IntersectionObserver);
