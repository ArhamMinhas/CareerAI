import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import Home from "./page";

describe("Home", () => {
  it("renders the CareerAI heading", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { name: "CareerAI" })).toBeInTheDocument();
  });

  it("links to the API health check", () => {
    render(<Home />);
    const link = screen.getByRole("link", { name: "Check API health" });
    expect(link).toHaveAttribute("href", expect.stringContaining("/api/v1/health"));
  });
});
