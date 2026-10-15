import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EmptyState } from "./empty-state";
import { ErrorState } from "./error-state";
import { LoadingSkeleton } from "./loading-skeleton";

describe("state components", () => {
  it("loading skeleton is a polite busy status with a text alternative", () => {
    render(<LoadingSkeleton variant="table" rows={3} />);
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-busy", "true");
    expect(status).toHaveTextContent("Loading");
  });

  it("empty state shows copy and an action link", () => {
    render(<EmptyState title="No predictions" description="Predict the next race." action={{ label: "Predict", href: "/predict" }} />);
    expect(screen.getByRole("heading", { name: "No predictions" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Predict" })).toHaveAttribute("href", "/predict");
  });

  it("error state announces itself and retries", () => {
    const retry = vi.fn();
    render(<ErrorState onRetry={retry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Could not load the data");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalledOnce();
  });
});
