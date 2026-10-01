import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "@/app/App";
import i18n from "@/lib/i18n";
import { installMockApi } from "./mockApi";

const PERSON = { id: "0199a000-0000-7000-8000-000000000002", display_name: "Ana" };
const SESSION = { username: "jose", language: "en", theme: "system" };

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

beforeEach(async () => {
  await i18n.changeLanguage("en");
});
afterEach(() => vi.unstubAllGlobals());

describe("behind a single sign-on proxy", () => {
  it("asks to sign in at the proxy instead of showing a form, even on a fresh instance", async () => {
    const state = installMockApi({ claimed: false, session: null, authMode: "proxy" });
    renderApp("/");
    expect(
      await screen.findByRole("heading", { name: "Sign in through single sign-on" }),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
    state.session = SESSION;
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "I have signed in" }));
    expect(await screen.findByRole("heading", { name: "Persons" })).toBeInTheDocument();
  });

  it("confirms a destructive action without asking for a password", async () => {
    const state = installMockApi({
      claimed: true,
      session: SESSION,
      persons: [PERSON],
      authMode: "proxy",
      trash: [
        { kind: "image", id: "t2", label: "Chest · close_up", person_id: PERSON.id, person_name: "Ana" },
      ],
    });
    renderApp("/trash");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Delete now" }));
    expect(await screen.findByText(/Confirm that you want to go ahead/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Go ahead" }));
    await waitFor(() => expect(state.trash).toEqual([]));
    expect(state.calls.find((c) => c.url.endsWith("/api/auth/sudo"))?.body).toEqual({});
  });
});
