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

function install(extra: Partial<MockState> = {}) {
  return installMockApi({
    claimed: true,
    session: SESSION,
    persons: [PERSON],
    lesions: [LESION],
    observations: [VISIT],
    ...extra,
  });
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
});
afterEach(() => vi.unstubAllGlobals());

describe("experimental proposals", () => {
  it("shows nothing when there are none", async () => {
    install();
    renderApp("/observations/o1");
    expect(await screen.findByRole("heading", { name: "Measurements" })).toBeInTheDocument();
    expect(screen.queryByText("Experimental")).not.toBeInTheDocument();
  });

  it("labels a proposal as experimental and records it only when used", async () => {
    const state = install({ proposals: { i1: [{ id: "p1", found: true, decision: "pending" }] } });
    renderApp("/observations/o1");
    expect(await screen.findByText("Experimental")).toBeInTheDocument();
    expect(screen.getByText("5.1 ± 0.2 mm × 4.9 ± 0.2 mm")).toBeInTheDocument();
    expect(screen.getByText("How clear the outline was: clear")).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Adjust it" })).toHaveAttribute(
      "href",
      "/observations/o1/measure/i1?proposal=p1",
    );
    expect(state.measurements).toHaveLength(0);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Use this measurement" }));
    await waitFor(() => expect(state.measurements).toHaveLength(1));
    expect(state.proposals.i1?.[0]?.decision).toBe("confirmed");
  });

  it("can be rejected, and says why when nothing could be outlined", async () => {
    const state = install({
      proposals: {
        i1: [
          { id: "p1", found: true, decision: "pending" },
          { id: "p0", found: false, reason: "low_contrast", decision: "automatic", framing: ["mark_small"] },
        ],
      },
    });
    renderApp("/observations/o1");
    expect(await screen.findByText(/differs too little from the skin around it/)).toBeInTheDocument();
    expect(screen.getByText(/come closer, so the mark fills more of the photo/)).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Reject" }));
    await waitFor(() => expect(state.proposals.i1?.[0]?.decision).toBe("rejected"));
    expect(state.measurements).toHaveLength(0);
  });
});
