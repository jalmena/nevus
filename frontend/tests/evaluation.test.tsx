import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "@/app/App";
import i18n from "@/lib/i18n";
import { installMockApi } from "./mockApi";

const PERSON = { id: "0199a000-0000-7000-8000-000000000002", display_name: "Ana" };
const SESSION = { username: "jose", language: "en", theme: "system" };
const VISIT = {
  id: "o1",
  lesion_id: "l1",
  captured_at: "2026-09-01T10:00:00Z",
  notes: null,
  symptoms: [],
  images: ["i1"],
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

beforeEach(async () => {
  await i18n.changeLanguage("en");
});
afterEach(() => vi.unstubAllGlobals());

describe("the evaluation set", () => {
  it("lists photos to label and labels one from the proposal", async () => {
    const state = installMockApi({
      claimed: true,
      session: SESSION,
      persons: [PERSON],
      observations: [VISIT],
    });
    renderApp("/evaluation");
    expect(await screen.findByText("No photo is labelled yet.")).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("link", { name: /Ana · Chest mark/ }));
    await user.click(await screen.findByRole("button", { name: "Start from the proposal" }));
    await user.click(screen.getByRole("radio", { name: "Good" }));
    await user.click(screen.getByRole("button", { name: "Save the label" }));
    await waitFor(() => expect(state.labels.i1?.quality).toBe("good"));
    expect(state.labels.i1?.outline).toHaveLength(4);
    expect(await screen.findByText("Label saved.")).toBeInTheDocument();
  });

  it("shows how the analyzer does per skin tone once photos are labelled", async () => {
    installMockApi({
      claimed: true,
      session: SESSION,
      persons: [PERSON],
      observations: [VISIT],
      labels: {
        i1: {
          outline: [
            [0, 0],
            [1, 0],
            [1, 1],
          ],
          quality: "good",
        },
      },
    });
    renderApp("/evaluation");
    const row = (await screen.findByRole("rowheader", { name: "MST3" })).closest("tr");
    if (!row) throw new Error("no row");
    expect(within(row).getByText("0.92")).toBeInTheDocument();
    expect(within(row).getByText("3% / 5%")).toBeInTheDocument();
  });
});
