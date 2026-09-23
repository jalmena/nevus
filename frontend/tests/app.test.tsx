import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "@/app/App";
import i18n from "@/lib/i18n";
import { installMockApi } from "./mockApi";

function renderApp(path = "/") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("claiming and signing in", () => {
  it("sends a visitor of a fresh instance to the claim page and creates the administrator", async () => {
    const state = installMockApi({ claimed: false });
    await i18n.changeLanguage("en");
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "Claim this instance" })).toBeInTheDocument();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Username"), "Jose");
    await user.type(screen.getByLabelText("Password"), "correct horse battery");
    await user.type(screen.getByLabelText("Repeat the password"), "correct horse battery");
    await user.click(screen.getByRole("button", { name: "Create the administrator" }));
    expect(await screen.findByRole("heading", { name: "Persons" })).toBeInTheDocument();
    expect(state.calls.some((c) => c.method === "POST" && c.url.endsWith("/api/auth/claim"))).toBe(true);
    expect(state.session?.username).toBe("jose");
  });

  it("shows the server's message on a wrong password", async () => {
    installMockApi({ claimed: true });
    await i18n.changeLanguage("en");
    renderApp("/login");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Username"), "jose");
    await user.type(screen.getByLabelText("Password"), "not the right password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Wrong username or password.");
  });

  it("refuses passwords shorter than ten characters before asking the server", async () => {
    const state = installMockApi({ claimed: true });
    await i18n.changeLanguage("en");
    renderApp("/login");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Username"), "jose");
    await user.type(screen.getByLabelText("Password"), "short");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("at least 10 characters");
    expect(state.calls.some((c) => c.url.endsWith("/api/auth/login"))).toBe(false);
  });
});

describe("persons", () => {
  it("lists the persons the user may see and creates a new one", async () => {
    const state = installMockApi({
      claimed: true,
      session: { username: "jose", language: "en", theme: "system" },
      persons: [{ id: "0199a000-0000-7000-8000-000000000002", display_name: "Ana" }],
    });
    await i18n.changeLanguage("en");
    renderApp("/");
    expect(await screen.findByText("Ana")).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Add a person" }));
    await user.type(screen.getByLabelText("Name"), "Bea");
    await user.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => expect(state.persons.map((p) => p.display_name)).toEqual(["Ana", "Bea"]));
    expect(await screen.findByText("Bea")).toBeInTheDocument();
  });

  it("applies the language stored with the account", async () => {
    installMockApi({
      claimed: true,
      session: { username: "jose", language: "es", theme: "dark" },
      persons: [],
    });
    await i18n.changeLanguage("en");
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "Personas" })).toBeInTheDocument();
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});
