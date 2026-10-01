import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "@/app/App";
import i18n from "@/lib/i18n";
import { installMockApi, type MockState } from "./mockApi";

const PERSON = { id: "0199a000-0000-7000-8000-000000000002", display_name: "Ana" };
const SESSION = { username: "jose", language: "en", theme: "system" };
const LESION = {
  id: "l1",
  person_id: PERSON.id,
  label: "Chest mark",
  zone: "1250",
  x: 0.4,
  y: 0.25,
  due: false,
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

function install(extra: Partial<MockState> = {}) {
  return installMockApi({ claimed: true, session: SESSION, persons: [PERSON], lesions: [LESION], ...extra });
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
});
afterEach(() => vi.unstubAllGlobals());

describe("reports", () => {
  it("makes the summary of every mark and offers the PDF once it is ready", async () => {
    const state = install();
    renderApp(`/persons/${PERSON.id}`);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Make the summary" }));
    await waitFor(() =>
      expect(state.calls.find((c) => c.method === "POST" && c.url.endsWith("/reports"))?.body).toEqual({
        scope: "profile",
        language: "en",
        paper: "a4",
      }),
    );
    expect(await screen.findByText("Summary of all marks")).toBeInTheDocument();
    const download = await screen.findByRole(
      "link",
      { name: /Download the PDF \(2 pages, 32 kB\)/ },
      { timeout: 4000 },
    );
    expect(download).toHaveAttribute("href", expect.stringMatching(/^\/api\/reports\/.+\/download$/));
  });

  it("makes a mark's record in the chosen language and paper", async () => {
    const state = install();
    renderApp("/lesions/l1");
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByRole("combobox", { name: "Language" }), "es");
    await user.selectOptions(screen.getByRole("combobox", { name: "Paper" }), "letter");
    await user.click(screen.getByRole("button", { name: "Make the record of this mark" }));
    await waitFor(() =>
      expect(state.calls.find((c) => c.method === "POST" && c.url.endsWith("/reports"))?.body).toEqual({
        scope: "lesion",
        lesion_id: "l1",
        language: "es",
        paper: "letter",
      }),
    );
    expect(await screen.findByText("Record of Chest mark")).toBeInTheDocument();
  });

  it("says when a report could not be made, and deletes it", async () => {
    const state = install({
      reports: [
        {
          id: "r1",
          scope: "profile",
          lesion_ids: [],
          language: "en",
          paper: "a4",
          status: "failed",
          fail: true,
        },
      ],
    });
    renderApp(`/persons/${PERSON.id}`);
    expect(await screen.findByText("The report could not be made.")).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Delete: Summary of all marks" }));
    await waitFor(() => expect(state.reports).toHaveLength(0));
  });
});
