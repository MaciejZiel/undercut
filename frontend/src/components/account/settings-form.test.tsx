import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockFetch } from "@/test/fetch-mock";
import { ME_USER, USER, renderWithProviders } from "@/test/render";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

import { SettingsScreen } from "./settings-form";

beforeEach(() => {
  document.cookie = "csrftoken=t; path=/";
  replace.mockReset();
  document.documentElement.removeAttribute("data-theme");
});
afterEach(() => vi.unstubAllGlobals());

describe("settings", () => {
  it("saves only through PATCH with the CSRF header and applies the theme", async () => {
    const m = mockFetch({
      "GET /api/v1/auth/me/": { body: ME_USER },
      "GET /api/v1/auth/google/": { body: { enabled: false, linked: false, email: null, has_password: true } },
      "PATCH /api/v1/account/settings/": ({ body }) => ({ body: { ...USER, ...(body as object) } }),
    });
    renderWithProviders(<SettingsScreen />);
    fireEvent.change(await screen.findByLabelText("Display name"), { target: { value: "Max Racer" } });
    fireEvent.click(screen.getByLabelText("dark"));
    fireEvent.click(screen.getByLabelText(/Send me a message after each race/));
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText("Settings saved.")).toBeInTheDocument();
    const patch = m.calls.find((c) => c.method === "PATCH")!;
    expect(patch.body).toEqual({ display_name: "Max Racer", timezone: "Europe/Warsaw", theme: "dark", race_result_email: false });
    expect(patch.headers.get("X-CSRFToken")).toBe("t");
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
  });

  it("shows API validation errors on the field", async () => {
    mockFetch({
      "GET /api/v1/auth/me/": { body: ME_USER },
      "GET /api/v1/auth/google/": { body: { enabled: false, linked: false, email: null, has_password: true } },
      "PATCH /api/v1/account/settings/": { status: 400, body: { detail: "This display name is reserved.", code: "display_name_reserved" } },
    });
    renderWithProviders(<SettingsScreen />);
    fireEvent.click(await screen.findByRole("button", { name: "Save changes" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("This display name is reserved.");
  });

  it("downloads the export through a Blob object URL, not a data URL", async () => {
    const created: Blob[] = [];
    const urlSpy = vi.fn((b: Blob) => (created.push(b), "blob:mock-1"));
    const revoke = vi.fn();
    Object.assign(URL, { createObjectURL: urlSpy, revokeObjectURL: revoke });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      expect(this.href).toBe("blob:mock-1");
      expect(this.download).toBe("undercut-export.json");
    });
    mockFetch({
      "GET /api/v1/auth/me/": { body: ME_USER },
      "GET /api/v1/auth/google/": { body: { enabled: false, linked: false, email: null, has_password: true } },
      "GET /api/v1/account/export/": new Response('{"user":{"id":7}}', { headers: { "Content-Type": "application/json" } }),
    });
    renderWithProviders(<SettingsScreen />);
    fireEvent.click(await screen.findByRole("button", { name: "Download my data" }));
    await waitFor(() => expect(click).toHaveBeenCalled());
    expect(urlSpy).toHaveBeenCalledTimes(1);
    expect(await created[0].text()).toContain('"user"');
    click.mockRestore();
  });

  it("requires typing the display name before deleting, then calls the API", async () => {
    const m = mockFetch({
      "GET /api/v1/auth/me/": { body: ME_USER },
      "GET /api/v1/auth/google/": { body: { enabled: false, linked: false, email: null, has_password: true } },
      "POST /api/v1/account/delete/": { status: 204 },
      "DELETE /api/v1/allauth/browser/v1/auth/session": { status: 401, body: {} },
    });
    renderWithProviders(<SettingsScreen />);
    fireEvent.click(await screen.findByRole("button", { name: "Delete my account" }));
    const dialog = await screen.findByRole("dialog", { name: "Delete your account?" });
    expect(within(dialog).getByText(/irreversible/i)).toBeInTheDocument();
    const confirm = within(dialog).getByRole("button", { name: "Delete forever" });
    expect(confirm).toBeDisabled();
    fireEvent.change(within(dialog).getByLabelText(/Type "Max Fan" to confirm/), { target: { value: "max fan" } });
    expect(confirm).toBeDisabled();
    fireEvent.change(within(dialog).getByLabelText(/Type "Max Fan" to confirm/), { target: { value: "Max Fan" } });
    expect(confirm).toBeEnabled();
    fireEvent.click(confirm);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/"));
    expect(m.calls.find((c) => c.url === "/api/v1/account/delete/")!.body).toEqual({ display_name: "Max Fan" });
  });

  it("locks the form for the demo account", async () => {
    mockFetch({ "GET /api/v1/auth/me/": { body: { is_authenticated: true, user: { ...USER, is_demo: true } } } });
    renderWithProviders(<SettingsScreen />);
    expect(await screen.findByText(/shared demo account/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save changes" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Delete my account" })).toBeDisabled();
  });
});
