import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
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

afterEach(() => vi.unstubAllGlobals());

describe("measuring a mark", () => {
  it("uses the detected card, proposes an outline from a tap, shows the size with its uncertainty and saves it", async () => {
    const state = installMockApi({
      claimed: true,
      session: SESSION,
      persons: [PERSON],
      lesions: [
        { id: "l1", person_id: PERSON.id, label: "Chest mark", zone: "1250", x: 0.4, y: 0.25, due: false },
      ],
      observations: [
        {
          id: "o1",
          lesion_id: "l1",
          captured_at: "2026-09-01T10:00:00Z",
          notes: null,
          symptoms: [],
          images: ["i1"],
        },
      ],
    });
    await i18n.changeLanguage("en");
    renderApp("/observations/o1/measure/i1");
    expect(await screen.findByText(/Reference card found, tilted 4°/)).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Use the reference card" }));
    const canvas = screen.getByRole("application", { name: /Tap the mark/ });
    await user.pointer([{ keys: "[MouseLeft]", target: canvas, coords: { clientX: 1500, clientY: 1125 } }]);
    await waitFor(() => expect(state.calls.some((c) => c.url.endsWith("/api/images/i1/fit"))).toBe(true));
    expect(await screen.findByText("5.1 ± 0.2 mm", {}, { timeout: 10_000 })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save the measurement" }));
    await waitFor(() => expect(state.measurements).toHaveLength(1));
    expect(await screen.findByRole("heading", { name: "Measurements" })).toBeInTheDocument();
    expect(await screen.findByText(/5\.1 ± 0\.2 mm × 4\.9 ± 0\.2 mm · card/)).toBeInTheDocument();
  });

  it("hides the uncertainty when the person chose so, but keeps the values", async () => {
    installMockApi({
      claimed: true,
      session: SESSION,
      persons: [PERSON],
      lesions: [
        { id: "l1", person_id: PERSON.id, label: "Chest mark", zone: "1250", x: 0.4, y: 0.25, due: false },
      ],
      observations: [
        {
          id: "o1",
          lesion_id: "l1",
          captured_at: "2026-09-01T10:00:00Z",
          notes: null,
          symptoms: [],
          images: ["i1"],
        },
      ],
    });
    const { formatMm } = await import("@/lib/measurements");
    expect(formatMm(4.44, 0.26, "en", true)).toBe("4.4 ± 0.3 mm");
    expect(formatMm(4.44, 0.26, "en", false)).toBe("4.4 mm");
    expect(formatMm(4.44, 0.04, "es", true)).toBe("4,4 ± 0,1 mm");
  });
});
