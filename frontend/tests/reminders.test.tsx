import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "@/app/App";
import i18n from "@/lib/i18n";
import { suggestName } from "@/lib/names";
import { installMockApi } from "./mockApi";

const PERSON = { id: "0199a000-0000-7000-8000-000000000002", display_name: "Ana" };

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

afterEach(() => vi.unstubAllGlobals());

describe("reminders", () => {
  it("lists what is due on the home page and snoozing takes it away", async () => {
    const state = installMockApi({
      claimed: true,
      session: { username: "jose", language: "en", theme: "system" },
      persons: [PERSON],
      lesions: [
        { id: "l1", person_id: PERSON.id, label: "Chest mark", zone: "1250", x: 0.4, y: 0.25, due: true },
      ],
    });
    await i18n.changeLanguage("en");
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "Due for a photo" })).toBeInTheDocument();
    const link = await screen.findByRole("link", { name: /Chest mark/ });
    expect(link).toHaveTextContent("Ana");
    const user = userEvent.setup();
    await user.click(link);
    await user.click(await screen.findByRole("button", { name: "In a week" }));
    await waitFor(() => expect(state.lesions[0]?.snoozed_until).toBe("2026-10-08"));
    expect(await screen.findByText(/Reminder snoozed until/)).toBeInTheDocument();
  });

  it("shows email delivery settings to administrators only", async () => {
    installMockApi({
      claimed: true,
      session: { username: "jose", language: "en", theme: "system", role: "admin" },
    });
    await i18n.changeLanguage("en");
    const { unmount } = renderApp("/settings");
    expect(
      await screen.findByRole("heading", { name: "Email delivery (administrator)" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Send me a daily email when marks are due" })).toBeDisabled();
    unmount();
    vi.unstubAllGlobals();
    installMockApi({
      claimed: true,
      session: { username: "ana", language: "en", theme: "system", role: "member" },
    });
    renderApp("/settings");
    expect(await screen.findByRole("heading", { name: "Reminders" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Email delivery (administrator)" })).not.toBeInTheDocument();
  });
});

describe("name suggestions", () => {
  it("combines two calm words in the person's language", () => {
    expect(suggestName("en", () => 0)).toBe("Quiet Pebble");
    expect(suggestName("es", () => 0)).toBe("Botón tranquilo");
  });
});
