import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockFetch } from "@/test/fetch-mock";
import { ME_ANON, ME_USER, USER, renderWithProviders } from "@/test/render";
import { UnverifiedBanner } from "./unverified-banner";

afterEach(() => vi.unstubAllGlobals());

describe("unverified e-mail banner", () => {
  it("is hidden for verified users and visitors", async () => {
    mockFetch({ "GET /api/v1/auth/me/": { body: ME_USER } });
    const { container } = renderWithProviders(<UnverifiedBanner />);
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  it("shows for unverified users and resends the link", async () => {
    document.cookie = "csrftoken=t; path=/";
    const m = mockFetch({
      "GET /api/v1/auth/me/": { body: { is_authenticated: true, user: { ...USER, email_verified: false, can_predict: false } } },
      "PUT /api/v1/allauth/browser/v1/account/email": { body: { status: 200 } },
    });
    renderWithProviders(<UnverifiedBanner />);
    fireEvent.click(await screen.findByRole("button", { name: "Resend link" }));
    expect(await screen.findByRole("button", { name: "Link sent" })).toBeDisabled();
    expect(m.calls.find((c) => c.method === "PUT")!.body).toEqual({ email: "max@example.com" });
  });

  it("renders nothing for anonymous visitors", async () => {
    const m = mockFetch({ "GET /api/v1/auth/me/": { body: ME_ANON } });
    const { container } = renderWithProviders(<UnverifiedBanner />);
    await waitFor(() => expect(m.count("GET /api/v1/auth/me/")).toBe(1));
    expect(container).toBeEmptyDOMElement();
  });
});
