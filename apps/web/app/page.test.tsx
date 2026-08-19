import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Home from "./page";

// jsdom has no WebGL context — the 3D scene is exercised visually, not in this test.
vi.mock("@/components/three/skill-network", () => ({
  SkillNetwork: () => <div data-testid="skill-network-stub" />,
}));

describe("Home", () => {
  it("renders the hero headline and primary CTA", () => {
    render(<Home />);
    expect(
      screen.getByRole("heading", { name: /turn your career into an intelligent roadmap/i })
    ).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Get started" }).length).toBeGreaterThan(0);
  });

  it("renders the navbar brand and section anchors", () => {
    render(<Home />);
    expect(screen.getByRole("link", { name: "CareerAI" })).toHaveAttribute("href", "/");
    const pricingLinks = screen.getAllByRole("link", { name: "Pricing" });
    expect(pricingLinks.length).toBeGreaterThan(0);
    for (const link of pricingLinks) {
      expect(link).toHaveAttribute("href", "#pricing");
    }
  });

  it("renders the FAQ section", () => {
    render(<Home />);
    expect(
      screen.getByRole("heading", { name: /questions people ask before signing up/i })
    ).toBeInTheDocument();
  });
});
