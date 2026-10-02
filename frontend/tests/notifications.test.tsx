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

describe("webhooks", () => {
  it("lets an administrator add an ntfy webhook and test it", async () => {
    const state = installMockApi({ claimed: true, session: SESSION, persons: [PERSON] });
    renderApp("/settings");
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByRole("combobox", { name: "Kind" }), "ntfy");
    expect(screen.getByText(/The topic address/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Address"), "https://ntfy.example/skin");
    await user.click(screen.getByRole("button", { name: "Add the webhook" }));
    await waitFor(() => expect(state.webhooks).toHaveLength(1));
    expect(state.webhooks[0]).toMatchObject({
      name: "ntfy",
      preset: "ntfy",
      url: "https://ntfy.example/skin",
    });
    await user.click(await screen.findByRole("button", { name: "Send a test to ntfy" }));
    expect(await screen.findByText("The test message arrived.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Delete the webhook ntfy" }));
    await waitFor(() => expect(state.webhooks).toHaveLength(0));
  });
});

describe("calendar link", () => {
  it("shows the link once with a warning, and stops it", async () => {
    const state = installMockApi({ claimed: true, session: SESSION, persons: [PERSON] });
    renderApp(`/persons/${PERSON.id}`);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Make a calendar link" }));
    expect(await screen.findByLabelText("Calendar link")).toHaveValue(
      "http://localhost/api/calendar/secret-token-123.ics",
    );
    expect(screen.getByText(/This link is shown only now/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Stop the link" }));
    await waitFor(() => expect(state.calendar.exists).toBe(false));
    expect(await screen.findByRole("button", { name: "Make a calendar link" })).toBeInTheDocument();
  });
});
