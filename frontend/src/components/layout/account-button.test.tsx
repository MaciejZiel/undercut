import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockFetch } from "@/test/fetch-mock";
import { ME_ANON, ME_USER, renderWithProviders } from "@/test/render";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace: vi.fn() }), usePathname: () => "/" }));

import { AccountButton } from "./account-button";

afterEach(() => vi.unstubAllGlobals());

describe("account button", () => {
  it("links visitors to the sign-in page", async () => {
    const m = mockFetch({ "GET /api/v1/auth/me/": { body: ME_ANON } });
    renderWithProviders(<AccountButton />);
    await waitFor(() => expect(m.count("GET /api/v1/auth/me/")).toBe(1));
    expect(screen.getByRole("link", { name: "Account: sign in" })).toHaveAttribute("href", "/login");
  });

  it("opens an avatar menu with the five entries and logs out", async () => {
    document.cookie = "csrftoken=t; path=/";
    const m = mockFetch({
      "GET /api/v1/auth/me/": { body: ME_USER },
      "DELETE /api/v1/allauth/browser/v1/auth/session": { status: 401, body: { status: 401 } },
    });
    renderWithProviders(<AccountButton />);
    const trigger = await screen.findByRole("button", { name: /Account menu for Max Fan/ });
    fireEvent.click(trigger);
    const items = screen.getAllByRole("menuitem").map((i) => i.textContent);
    expect(items).toEqual(["My F1", "My picks", "Leagues", "Settings", "Log out"]);
    expect(screen.getByRole("menuitem", { name: "Settings" })).toHaveAttribute("href", "/settings");
    fireEvent.click(screen.getByRole("menuitem", { name: "Log out" }));
    await waitFor(() => expect(m.calls.some((c) => c.method === "DELETE")).toBe(true));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/"));
    expect(await screen.findByRole("link", { name: "Account: sign in" })).toBeInTheDocument();
  });

  it("closes on Escape and returns focus to the trigger", async () => {
    mockFetch({ "GET /api/v1/auth/me/": { body: ME_USER } });
    renderWithProviders(<AccountButton />);
    const trigger = await screen.findByRole("button", { name: /Account menu/ });
    fireEvent.click(trigger);
    fireEvent.keyDown(screen.getAllByRole("menuitem")[0], { key: "Escape" });
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});
