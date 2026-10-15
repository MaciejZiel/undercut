import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockFetch } from "@/test/fetch-mock";
import { ME_ANON, ME_USER, renderWithProviders } from "@/test/render";

const replace = vi.fn();
let search = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(search),
  usePathname: () => "/login",
}));

import { LoginScreen, RegisterScreen, RequestResetScreen, VerifyEmailScreen } from "./auth-forms";

beforeEach(() => {
  replace.mockReset();
  search = "";
  document.cookie = "csrftoken=tok; path=/";
});
afterEach(() => vi.unstubAllGlobals());

function fillLogin() {
  fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "max@example.com" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "hunter2hunter2" } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("login", () => {
  it("keeps the button active and names the missing fields instead", async () => {
    mockFetch({ "GET /api/v1/auth/me/": { body: ME_ANON } });
    renderWithProviders(<LoginScreen />);
    const button = screen.getByRole("button", { name: "Sign in" });
    expect(button).toBeEnabled();
    fireEvent.click(button);
    expect(await screen.findByText("Enter your e-mail address.")).toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();
  });
  it("shows the API error for wrong credentials", async () => {
    mockFetch({
      "GET /api/v1/auth/me/": { body: ME_ANON },
      "POST /api/v1/allauth/browser/v1/auth/login": {
        status: 400,
        body: { status: 400, errors: [{ message: "The email address and/or password you specified are not correct.", code: "email_password_mismatch", param: "password" }] },
      },
    });
    renderWithProviders(<LoginScreen />);
    fillLogin();
    expect(await screen.findByText("The email address and/or password you specified are not correct.")).toBeInTheDocument();
  });

  it("shows the rate-limit message on 429", async () => {
    mockFetch({
      "GET /api/v1/auth/me/": { body: ME_ANON },
      "POST /api/v1/allauth/browser/v1/auth/login": { status: 429, body: { status: 429 } },
    });
    renderWithProviders(<LoginScreen />);
    fillLogin();
    expect(await screen.findByRole("alert")).toHaveTextContent(/too many attempts/i);
  });

  it("signs in, refreshes /me and returns to the page kept in ?next", async () => {
    search = "next=%2Fpredict%2F2026%2F3";
    let signedIn = false;
    const m = mockFetch({
      "GET /api/v1/auth/me/": () => ({ body: signedIn ? ME_USER : ME_ANON }),
      "POST /api/v1/allauth/browser/v1/auth/login": () => {
        signedIn = true;
        return { body: { status: 200 } };
      },
    });
    renderWithProviders(<LoginScreen />);
    await waitFor(() => expect(m.count("GET /api/v1/auth/me/")).toBe(1));
    fillLogin();
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/predict/2026/3"));
    const login = m.calls.find((c) => c.method === "POST")!;
    expect(login.body).toEqual({ email: "max@example.com", password: "hunter2hunter2" });
    expect(login.headers.get("X-CSRFToken")).toBe("tok");
  });

  it("ignores an unsafe ?next", async () => {
    search = "next=https%3A%2F%2Fevil.com";
    let signedIn = false;
    mockFetch({
      "GET /api/v1/auth/me/": () => ({ body: signedIn ? ME_USER : ME_ANON }),
      "POST /api/v1/allauth/browser/v1/auth/login": () => {
        signedIn = true;
        return { body: {} };
      },
    });
    renderWithProviders(<LoginScreen />);
    fillLogin();
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/"));
  });
});

describe("register", () => {
  it("shows field errors from the API under the right field", async () => {
    mockFetch({
      "GET /api/v1/auth/me/": { body: ME_ANON },
      "POST /api/v1/allauth/browser/v1/auth/signup": {
        status: 400,
        body: { status: 400, errors: [{ message: "This display name is already taken.", code: "taken", param: "display_name" }] },
      },
    });
    renderWithProviders(<RegisterScreen />);
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "a@b.co" } });
    fireEvent.change(screen.getByLabelText("Display name"), { target: { value: "Taken" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "pw-pw-pw-pw-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByText("This display name is already taken.")).toBeInTheDocument();
    expect(screen.getByLabelText("Display name")).toHaveAttribute("aria-invalid", "true");
  });

  it("tells the user to check their inbox after sign-up", async () => {
    mockFetch({
      "GET /api/v1/auth/me/": { body: ME_ANON },
      "POST /api/v1/allauth/browser/v1/auth/signup": { body: { status: 200 } },
    });
    renderWithProviders(<RegisterScreen />);
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "a@b.co" } });
    fireEvent.change(screen.getByLabelText("Display name"), { target: { value: "Newbie" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "pw-pw-pw-pw-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByRole("heading", { name: "Check your inbox" })).toBeInTheDocument();
  });
});

describe("verify e-mail and reset", () => {
  it("validates the key, then confirms on click (401 after confirm still counts as success)", async () => {
    const m = mockFetch({
      "GET /api/v1/auth/me/": { body: ME_ANON },
      "GET /api/v1/allauth/browser/v1/auth/email/verify": { body: { status: 200, data: { email: "max@example.com" } } },
      "POST /api/v1/allauth/browser/v1/auth/email/verify": { status: 401, body: { status: 401 } },
    });
    renderWithProviders(<VerifyEmailScreen verifyKey="KEY1" />);
    fireEvent.click(await screen.findByRole("button", { name: "Confirm e-mail" }));
    expect(await screen.findByText("Your e-mail address is confirmed.")).toBeInTheDocument();
    expect(m.calls.find((c) => c.method === "GET" && c.url.includes("email/verify"))!.headers.get("X-Email-Verification-Key")).toBe("KEY1");
    expect(m.calls.find((c) => c.method === "POST")!.body).toEqual({ key: "KEY1" });
  });

  it("explains an invalid link", async () => {
    mockFetch({
      "GET /api/v1/auth/me/": { body: ME_ANON },
      "GET /api/v1/allauth/browser/v1/auth/email/verify": { status: 400, body: { status: 400, errors: [{ message: "bad", code: "invalid_or_expired_key", param: "key" }] } },
    });
    renderWithProviders(<VerifyEmailScreen verifyKey="BAD" />);
    expect(await screen.findByText("This link is invalid or has expired. Request a new one.")).toBeInTheDocument();
  });

  it("gives the same answer for the reset request whatever the address", async () => {
    mockFetch({
      "GET /api/v1/auth/me/": { body: ME_ANON },
      "POST /api/v1/allauth/browser/v1/auth/password/request": { body: { status: 200 } },
    });
    renderWithProviders(<RequestResetScreen />);
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "who@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));
    expect(await screen.findByText(/If an account exists for who@example.com/)).toBeInTheDocument();
  });
});
