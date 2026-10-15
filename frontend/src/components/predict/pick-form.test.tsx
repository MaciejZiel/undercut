import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockFetch } from "@/test/fetch-mock";
import { ME_ANON, ME_USER, USER, renderWithProviders } from "@/test/render";
import type { PickableDriver, RoundState } from "@/lib/predict/api";

const push = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), push }) }));

import { PickForm, podiumTaken } from "./pick-form";

const drivers: PickableDriver[] = [
  { id: 1, name: "Max Verstappen", code: "VER", number: 1 },
  { id: 2, name: "Lando Norris", code: "NOR", number: 4 },
  { id: 3, name: "Oscar Piastri", code: "PIA", number: 81 },
  { id: 4, name: "Charles Leclerc", code: "LEC", number: 16 },
];
const round = { id: 9, year: 2026, round: 3, name: "Australian Grand Prix" };
const future = () => new Date(Date.now() + 3600_000).toISOString();
const stateOf = (status: RoundState["status"], my_pick: RoundState["my_pick"] = null, closes_at: string | null = future()): RoundState => ({ round, status, closes_at, my_pick });

beforeEach(() => {
  sessionStorage.clear();
  document.cookie = "csrftoken=t; path=/";
});
afterEach(() => vi.unstubAllGlobals());

function choose(label: string, option: string) {
  const input = screen.getByRole("combobox", { name: label });
  fireEvent.focus(input);
  fireEvent.click(within(screen.getByRole("listbox", { name: label })).getByRole("option", { name: new RegExp(option) }));
}

async function renderForm(state: RoundState, me: unknown = ME_USER, extra: Parameters<typeof mockFetch>[0] = {}) {
  const m = mockFetch({ "GET /api/v1/auth/me/": { body: me }, ...extra });
  const utils = renderWithProviders(<PickForm year={2026} round={3} result={{ state, skewMs: 0 }} drivers={drivers} />);
  await screen.findByRole("combobox", { name: "Winner (P1)" }).catch(() => undefined);
  await waitFor(() => expect(m.count("GET /api/v1/auth/me/")).toBe(1));
  return { m, ...utils };
}

describe("pick form for a guest", () => {
  it("lets a guest fill the form in and sends them to sign in when saving, keeping the draft", async () => {
    push.mockReset();
    sessionStorage.clear();
    await renderForm(stateOf("open"), ME_ANON);
    choose("Winner (P1)", "Verstappen");
    choose("Second place (P2)", "Norris");
    choose("Third place (P3)", "Piastri");
    choose("Pole position", "Leclerc");
    choose("Fastest lap", "Norris");
    fireEvent.click(screen.getByRole("button", { name: "Sign in to save pick" }));
    expect(push).toHaveBeenCalledWith("/login?next=%2Fpredict%2F2026%2F3");
    expect(JSON.parse(sessionStorage.getItem("undercut:draft:2026:3") as string)).toEqual({ p1: 1, p2: 2, p3: 3, pole: 4, fastest_lap: 2 });
  });
  it("shows how a pick scores", async () => {
    await renderForm(stateOf("open"), ME_ANON);
    expect(screen.getByText(/5 points for the right driver/)).toBeInTheDocument();
  });
});

describe("pick form", () => {
  it("renders the five fields", async () => {
    await renderForm(stateOf("open"));
    for (const label of ["Winner (P1)", "Second place (P2)", "Third place (P3)", "Pole position", "Fastest lap"]) {
      expect(screen.getByRole("combobox", { name: label })).toBeInTheDocument();
    }
  });

  it("keeps a podium driver out of the other podium slots but allows him for pole and fastest lap", async () => {
    await renderForm(stateOf("open"));
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Winner (P1)" })).toBeEnabled());
    choose("Winner (P1)", "Verstappen");
    const p2 = screen.getByRole("combobox", { name: "Second place (P2)" });
    fireEvent.focus(p2);
    expect(within(screen.getByRole("listbox", { name: "Second place (P2)" })).getByRole("option", { name: /Verstappen/ })).toHaveAttribute("aria-disabled", "true");
    fireEvent.keyDown(p2, { key: "Escape" });
    const pole = screen.getByRole("combobox", { name: "Pole position" });
    fireEvent.focus(pole);
    expect(within(screen.getByRole("listbox", { name: "Pole position" })).getByRole("option", { name: /Verstappen/ })).not.toHaveAttribute("aria-disabled");
    expect(podiumTaken({ p1: 1, p2: null, p3: 3, pole: 1, fastest_lap: null }, "p2")).toEqual(new Set([1, 3]));
  });

  it("refuses to submit an incomplete pick", async () => {
    const { m } = await renderForm(stateOf("open"));
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Winner (P1)" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Save pick" }));
    expect(await screen.findByText("Choose a driver for every field.")).toBeInTheDocument();
    expect(m.calls.some((c) => c.method === "PUT")).toBe(false);
  });

  it("submits ids with the CSRF header and confirms", async () => {
    const saved = stateOf("open", { p1: { id: 1, name: "Max Verstappen", code: "VER" }, p2: { id: 2, name: "Lando Norris", code: "NOR" }, p3: { id: 3, name: "Oscar Piastri", code: "PIA" }, pole: { id: 4, name: "Charles Leclerc", code: "LEC" }, fastest_lap: { id: 1, name: "Max Verstappen", code: "VER" }, points: null, breakdown: {}, updated_at: "2026-03-01T00:00:00Z" });
    const { m } = await renderForm(stateOf("open"), ME_USER, { "PUT /api/v1/predictions/rounds/2026/3/": { status: 201, body: saved } });
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Winner (P1)" })).toBeEnabled());
    choose("Winner (P1)", "Verstappen");
    choose("Second place (P2)", "Norris");
    choose("Third place (P3)", "Piastri");
    choose("Pole position", "Leclerc");
    choose("Fastest lap", "Verstappen");
    fireEvent.click(screen.getByRole("button", { name: "Save pick" }));
    expect(await screen.findByText(/Pick saved\./)).toBeInTheDocument();
    const put = m.calls.find((c) => c.method === "PUT")!;
    expect(put.body).toEqual({ p1: 1, p2: 2, p3: 3, pole: 4, fastest_lap: 1 });
    expect(put.headers.get("X-CSRFToken")).toBe("t");
  });

  it("shows the lock message when the server answers 403 on save", async () => {
    const pick = { p1: { id: 1, name: "A", code: null }, p2: { id: 2, name: "B", code: null }, p3: { id: 3, name: "C", code: null }, pole: { id: 4, name: "D", code: null }, fastest_lap: { id: 1, name: "A", code: null }, points: null, breakdown: {}, updated_at: "x" };
    await renderForm(stateOf("open", pick), ME_USER, {
      "PUT /api/v1/predictions/rounds/2026/3/": { status: 403, body: { detail: "closed", code: "predictions_locked" } },
    });
    await waitFor(() => expect(screen.getByRole("button", { name: "Update pick" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Update pick" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Predictions for this round are closed.");
  });

  it("is read-only once the server reports the round as closed", async () => {
    const pick = { p1: { id: 1, name: "Max Verstappen", code: "VER" }, p2: null, p3: null, pole: null, fastest_lap: null, points: 12, breakdown: {}, updated_at: "x" };
    await renderForm(stateOf("closed", pick));
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /save|update/i })).not.toBeInTheDocument();
    expect(screen.getByText(/Predictions for this round are closed/)).toBeInTheDocument();
    expect(screen.getByText("Max Verstappen")).toBeInTheDocument();
  });

  it("treats a reached countdown as locked using the server clock offset", async () => {
    const m = mockFetch({ "GET /api/v1/auth/me/": { body: ME_USER } });
    // server clock is 2 h ahead of the browser, so a lock 1 h from "browser now" has passed for the server
    renderWithProviders(<PickForm year={2026} round={3} result={{ state: stateOf("open", null, future()), skewMs: 2 * 3600_000 }} drivers={drivers} />);
    await waitFor(() => expect(m.count("GET /api/v1/auth/me/")).toBe(1));
    expect(await screen.findByText(/Predictions for this round are closed/)).toBeInTheDocument();
  });

  it("explains that an unconfirmed e-mail cannot predict", async () => {
    await renderForm(stateOf("open"), { is_authenticated: true, user: { ...USER, email_verified: false, can_predict: false } });
    expect(await screen.findByText(/Confirm your e-mail address to make predictions/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save pick" })).toBeDisabled();
  });
});
