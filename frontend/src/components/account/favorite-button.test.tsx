import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockFetch } from "@/test/fetch-mock";
import { ME_ANON, ME_USER, renderWithProviders } from "@/test/render";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

import { FavoriteButton } from "./favorite-button";

const limits = { drivers: 10, constructors: 5 };
const favs = (drivers: { slug: string; name: string; code: string | null }[] = []) => ({ drivers, constructors: [], limits });

beforeEach(() => {
  document.cookie = "csrftoken=tok; path=/";
});
afterEach(() => vi.unstubAllGlobals());

describe("favourite button", () => {
  it("toggles optimistically and keeps the new state when the server agrees", async () => {
    let stored = favs();
    let release: () => void = () => {};
    const gate = new Promise<void>((r) => (release = r));
    const m = mockFetch({
      "GET /api/v1/auth/me/": { body: ME_USER },
      "GET /api/v1/favorites/": () => ({ body: stored }),
      "PUT /api/v1/favorites/drivers/max/": () => {
        stored = favs([{ slug: "max", name: "Max V", code: "VER" }]);
        return { body: { favorite: true } };
      },
    });
    // delay the PUT so the optimistic state is observable
    const original = globalThis.fetch;
    vi.stubGlobal("fetch", async (...args: Parameters<typeof fetch>) => {
      if ((args[1]?.method ?? "GET") === "PUT") await gate;
      return original(...args);
    });
    renderWithProviders(<FavoriteButton kind="driver" slug="max" name="Max V" />);
    const button = await screen.findByRole("button", { name: "Follow Max V" });
    await waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(button);
    expect(await screen.findByRole("button", { name: "Unfollow Max V" })).toHaveAttribute("aria-pressed", "true");
    release();
    await waitFor(() => expect(m.calls.some((c) => c.method === "PUT")).toBe(true));
    expect(screen.getByRole("button", { name: "Unfollow Max V" })).toBeInTheDocument();
  });

  it("rolls back and shows the limits message when the server answers 409", async () => {
    mockFetch({
      "GET /api/v1/auth/me/": { body: ME_USER },
      "GET /api/v1/favorites/": { body: favs() },
      "PUT /api/v1/favorites/drivers/max/": { status: 409, body: { detail: "limit", code: "favorite_limit" } },
    });
    renderWithProviders(<FavoriteButton kind="driver" slug="max" name="Max V" />);
    const button = await screen.findByRole("button", { name: "Follow Max V" });
    await waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(button);
    expect(await screen.findByText("You can follow up to 10 drivers. Unfollow one to add another.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Follow Max V" })).toHaveAttribute("aria-pressed", "false");
  });

  it("blocks locally when the limit is already reached", async () => {
    const full = Array.from({ length: 5 }, (_, i) => ({ slug: `t${i}`, name: `T${i}` }));
    const m = mockFetch({
      "GET /api/v1/auth/me/": { body: ME_USER },
      "GET /api/v1/favorites/": { body: { drivers: [], constructors: full, limits } },
    });
    renderWithProviders(<FavoriteButton kind="constructor" slug="new" name="New Team" />);
    const button = await screen.findByRole("button", { name: "Follow New Team" });
    await waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(button);
    expect(await screen.findByText("You can follow up to 5 constructors. Unfollow one to add another.")).toBeInTheDocument();
    expect(m.calls.some((c) => c.method === "PUT")).toBe(false);
  });

  it("opens the sign-in dialog for visitors and follows after login", async () => {
    let signedIn = false;
    const m = mockFetch({
      "GET /api/v1/auth/me/": () => ({ body: signedIn ? ME_USER : ME_ANON }),
      "GET /api/v1/favorites/": { body: favs() },
      "POST /api/v1/allauth/browser/v1/auth/login": () => {
        signedIn = true;
        return { body: { status: 200 } };
      },
      "PUT /api/v1/favorites/drivers/max/": { body: { favorite: true } },
    });
    renderWithProviders(<FavoriteButton kind="driver" slug="max" name="Max V" />);
    const btn = await screen.findByRole("button", { name: "Follow Max V" });
    await waitFor(() => expect(btn).toBeEnabled());
    fireEvent.click(btn);
    const dialog = await screen.findByRole("dialog", { name: "Sign in to follow" });
    fireEvent.change(within(dialog).getByLabelText("E-mail"), { target: { value: "max@example.com" } });
    fireEvent.change(within(dialog).getByLabelText("Password"), { target: { value: "pw" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(m.calls.some((c) => c.method === "PUT" && c.url === "/api/v1/favorites/drivers/max/")).toBe(true));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("closes the dialog with Escape without doing anything", async () => {
    const m = mockFetch({ "GET /api/v1/auth/me/": { body: ME_ANON } });
    renderWithProviders(<FavoriteButton kind="driver" slug="max" name="Max V" />);
    const btn = await screen.findByRole("button", { name: "Follow Max V" });
    await waitFor(() => expect(btn).toBeEnabled());
    fireEvent.click(btn);
    fireEvent.keyDown(await screen.findByRole("dialog"), { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(m.calls.some((c) => c.method === "PUT")).toBe(false);
  });
});
