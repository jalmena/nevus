import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "@/app/App";
import i18n from "@/lib/i18n";
import { installMockApi } from "./mockApi";

const SESSION = { username: "jose", language: "en", theme: "system" };
const ME = {
  id: "0199a000-0000-7000-8000-000000000001",
  username: "jose",
  role: "admin",
  disabled_at: null,
  totp_enabled: false,
  last_login_at: "2026-10-01T10:00:00Z",
};
const ANA = {
  id: "u2",
  username: "ana",
  role: "member",
  disabled_at: null,
  totp_enabled: true,
  last_login_at: null,
};

function renderApp(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

/** The sudo dialog: the password again, for the actions the server protects. */
async function confirmPassword(user: ReturnType<typeof userEvent.setup>) {
  const dialog = await screen.findByRole("dialog");
  await user.type(within(dialog).getByLabelText("Password"), "correct horse battery");
  await user.click(within(dialog).getByRole("button", { name: "Confirm" }));
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
});
afterEach(() => vi.unstubAllGlobals());

describe("signing in with a second factor", () => {
  it("asks for the code after the password, and takes a recovery code instead", async () => {
    const state = installMockApi({
      claimed: true,
      totp: { enabled: true, settingUp: false, codesLeft: 10, pending: false },
    });
    renderApp("/login");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Username"), "jose");
    await user.type(screen.getByLabelText("Password"), "correct horse battery");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "One more step" })).toBeInTheDocument();
    expect(state.session).toBeNull();

    await user.type(screen.getByLabelText("Code from the authenticator"), "000000");
    await user.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Wrong code.");
    await user.click(screen.getByRole("button", { name: "Use a recovery code instead" }));
    await user.type(screen.getByLabelText("Recovery code"), "AAAAA-BBBBB");
    await user.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByRole("heading", { name: "Persons" })).toBeInTheDocument();
    expect(state.totp.codesLeft).toBe(9);
  });
});

describe("the second factor in the settings", () => {
  it("is set up with a QR code and a first code, hands out the recovery codes once, and turns off", async () => {
    const state = installMockApi({ claimed: true, session: SESSION });
    renderApp("/settings");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Set up a second factor" }));
    await confirmPassword(user);
    expect(await screen.findByRole("img", { name: /QR code for the authenticator app/ })).toBeInTheDocument();
    expect(screen.getByText("JBSW Y3DP EHPK 3PXP JBSW Y3DP EHPK 3PXP")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Code the app shows now"), "12 34 56");
    await user.click(screen.getByRole("button", { name: "Turn the second factor on" }));
    const codes = await screen.findByRole("region", { name: "Recovery codes" });
    expect(within(codes).getAllByRole("listitem")).toHaveLength(10);
    expect(state.totp.enabled).toBe(true);
    await user.click(within(codes).getByRole("button", { name: "I have saved them" }));
    expect(await screen.findByText("The second factor is on. 10 recovery codes left.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Turn it off" }));
    await waitFor(() => expect(state.totp.enabled).toBe(false));
    expect(await screen.findByRole("button", { name: "Set up a second factor" })).toBeInTheDocument();
  });
});

describe("accounts administration", () => {
  it("lists the accounts, creates one, disables one and turns a lost second factor off", async () => {
    const state = installMockApi({ claimed: true, session: SESSION, users: [ME, ANA] });
    renderApp("/settings");
    const user = userEvent.setup();
    expect(await screen.findByRole("heading", { name: "Accounts (administrator)" })).toBeInTheDocument();
    expect(await screen.findByText("ana")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Disable the account jose" })).not.toBeInTheDocument();

    await user.type(screen.getByLabelText("Username"), "Luis");
    await user.type(screen.getByLabelText("Temporary password"), "a temporary password");
    await user.click(screen.getByRole("button", { name: "Create the account" }));
    await waitFor(() => expect(state.users.map((account) => account.username)).toContain("luis"));
    expect(await screen.findByText("luis")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Disable the account ana" }));
    expect(await screen.findByRole("button", { name: "Enable the account ana" })).toBeInTheDocument();
    expect(state.users.find((account) => account.username === "ana")?.disabled_at).not.toBeNull();

    await user.click(screen.getByRole("button", { name: "Turn the second factor off for ana" }));
    await confirmPassword(user);
    await waitFor(() =>
      expect(state.users.find((account) => account.username === "ana")?.totp_enabled).toBe(false),
    );
    expect(await screen.findByText(/The second factor is off for that account/)).toBeInTheDocument();
  });
});
