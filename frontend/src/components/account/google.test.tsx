import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { googleErrorMessage, googleStartUrl } from "@/lib/auth/google";
import { mockFetch } from "@/test/fetch-mock";
import { ME_USER, renderWithProviders } from "@/test/render";

let search = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(search),
  usePathname: () => "/login",
}));

import { GoogleButton } from "./google-button";
import { SettingsScreen } from "./settings-form";

const off = { enabled: false, linked: false, email: null, has_password: false };

beforeEach(() => {
  search = "";
  document.cookie = "csrftoken=t; path=/";
});
afterEach(() => vi.unstubAllGlobals());

describe("google helpers", () => {
  it("builds the start URL with only the parameters that matter", () => {
    expect(googleStartUrl()).toBe("/api/v1/auth/google/start/");
    expect(googleStartUrl("/predict")).toBe("/api/v1/auth/google/start/?next=%2Fpredict");
    expect(googleStartUrl(null, "link")).toBe("/api/v1/auth/google/start/?mode=link");
  });

  it("explains known errors and falls back for unknown ones", () => {
    expect(googleErrorMessage("cancelled")).toMatch(/cancelled/);
    expect(googleErrorMessage("weird")).toMatch(/failed/);
    expect(googleErrorMessage(null)).toBeNull();
  });
});

describe("google button", () => {
  it("is hidden when the backend has no Google keys", async () => {
    const m = mockFetch({ "GET /api/v1/auth/google/": { body: off } });
    renderWithProviders(<GoogleButton />);
    await waitFor(() => expect(m.count("GET /api/v1/auth/google/")).toBe(1));
    expect(screen.queryByText("Continue with Google")).not.toBeInTheDocument();
  });

  it("links to the backend start URL, keeping the return path", async () => {
    mockFetch({ "GET /api/v1/auth/google/": { body: { ...off, enabled: true } } });
    renderWithProviders(<GoogleButton next="/predict" />);
    const link = await screen.findByRole("link", { name: /Continue with Google/ });
    expect(link).toHaveAttribute("href", "/api/v1/auth/google/start/?next=%2Fpredict");
  });
});

describe("google settings section", () => {
  it("offers to link when nothing is linked", async () => {
    mockFetch({
      "GET /api/v1/auth/me/": { body: ME_USER },
      "GET /api/v1/auth/google/": { body: { ...off, enabled: true, has_password: true } },
    });
    renderWithProviders(<SettingsScreen />);
    const link = await screen.findByRole("link", { name: "Link Google" });
    expect(link).toHaveAttribute("href", "/api/v1/auth/google/start/?mode=link&next=%2Fsettings");
  });

  it("unlinks through DELETE with the CSRF header", async () => {
    const status = { enabled: true, linked: true, email: "max@gmail.com", has_password: true };
    const m = mockFetch({
      "GET /api/v1/auth/me/": { body: ME_USER },
      "GET /api/v1/auth/google/": { body: status },
      "DELETE /api/v1/auth/google/": { status: 204 },
    });
    renderWithProviders(<SettingsScreen />);
    expect(await screen.findByText("max@gmail.com")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Unlink Google" }));
    await waitFor(() => expect(m.calls.some((c) => c.method === "DELETE")).toBe(true));
    expect(m.calls.find((c) => c.method === "DELETE")!.headers.get("X-CSRFToken")).toBe("t");
  });

  it("blocks unlinking when Google is the only way in", async () => {
    mockFetch({
      "GET /api/v1/auth/me/": { body: ME_USER },
      "GET /api/v1/auth/google/": { body: { enabled: true, linked: true, email: "max@gmail.com", has_password: false } },
    });
    renderWithProviders(<SettingsScreen />);
    expect(await screen.findByRole("button", { name: "Unlink Google" })).toBeDisabled();
    expect(screen.getByText(/no password yet/)).toBeInTheDocument();
  });

  it("shows the reason when linking failed", async () => {
    search = "google_error=google_in_use";
    mockFetch({
      "GET /api/v1/auth/me/": { body: ME_USER },
      "GET /api/v1/auth/google/": { body: { ...off, enabled: true } },
    });
    renderWithProviders(<SettingsScreen />);
    expect(await screen.findByText(/already linked to another/)).toBeInTheDocument();
  });
});
