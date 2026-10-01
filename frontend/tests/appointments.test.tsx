import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "@/app/App";
import { daysUntil } from "@/lib/appointments";
import i18n from "@/lib/i18n";
import { installMockApi, type MockState } from "./mockApi";

const PERSON = { id: "0199a000-0000-7000-8000-000000000002", display_name: "Ana" };
const SESSION = { username: "jose", language: "en", theme: "system" };
const LESIONS = [
  { id: "l1", person_id: PERSON.id, label: "Chest mark", zone: "1250", x: 0.4, y: 0.25, due: false },
  { id: "l2", person_id: PERSON.id, label: null, zone: "2300", x: 0.5, y: 0.45, due: false },
];
const VISITS = [
  {
    id: "o1",
    lesion_id: "l1",
    captured_at: "2026-06-01T10:00:00Z",
    notes: null,
    symptoms: [],
    images: ["i1"],
  },
];

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
    lesions: LESIONS,
    observations: VISITS,
    ...extra,
  });
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
});
afterEach(() => vi.unstubAllGlobals());

describe("preparing an appointment", () => {
  it("plans one from the person's page and lists what to photograph", async () => {
    const state = install();
    renderApp(`/persons/${PERSON.id}`);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Date of the appointment"), "2026-10-20");
    await user.type(screen.getByLabelText("Note (optional)"), "Dermatology");
    await user.click(screen.getByRole("button", { name: "Prepare the appointment" }));
    await waitFor(() => expect(state.appointments).toHaveLength(1));
    expect(await screen.findByRole("heading", { name: /Appointment on .*20.* 2026/ })).toBeInTheDocument();
    expect(screen.getByText("Dermatology")).toBeInTheDocument();
    const todo = screen
      .getByRole("heading", { name: "To photograph before the appointment" })
      .closest("section");
    if (!todo) throw new Error("no checklist");
    expect(within(todo).getByRole("link", { name: "Chest mark" })).toBeInTheDocument();
    expect(within(todo).getByText("Never photographed")).toBeInTheDocument();
    expect(within(todo).getByText("0 of 2 ready")).toBeInTheDocument();
  });

  it("starts a visit of a mark from the list", async () => {
    const state = install({
      appointments: [
        {
          id: "a1",
          person_id: PERSON.id,
          date: "2026-10-20",
          notes: null,
          report_id: null,
          created_at: "2026-10-01T10:00:00Z",
        },
      ],
    });
    renderApp("/appointments/a1");
    const user = userEvent.setup();
    const buttons = await screen.findAllByRole("button", { name: "Photograph now" });
    await user.click(buttons[0] as HTMLElement);
    await waitFor(() => expect(state.observations.length).toBe(2));
    expect(await screen.findByRole("heading", { name: "Photos" })).toBeInTheDocument();
  });

  it("makes the appointment's report and offers it", async () => {
    const state = install({
      appointments: [
        {
          id: "a1",
          person_id: PERSON.id,
          date: "2026-10-20",
          notes: null,
          report_id: null,
          created_at: "2026-10-01T10:00:00Z",
        },
      ],
    });
    renderApp("/appointments/a1");
    const user = userEvent.setup();
    await user.selectOptions(await screen.findByRole("combobox", { name: "Language" }), "es");
    await user.click(screen.getByRole("button", { name: "Make the report" }));
    await waitFor(() => expect(state.reports[0]?.scope).toBe("visit"));
    expect(state.reports[0]?.language).toBe("es");
    expect(
      await screen.findByRole("link", { name: /Download the PDF/ }, { timeout: 4000 }),
    ).toBeInTheDocument();
  });

  it("shows the coming appointments on the home page", async () => {
    install({
      appointments: [
        {
          id: "a1",
          person_id: PERSON.id,
          date: "2026-10-20",
          notes: null,
          report_id: null,
          created_at: "2026-10-01T10:00:00Z",
        },
      ],
    });
    renderApp("/");
    const upcoming = await screen.findByRole("heading", { name: "Coming appointments" });
    const section = upcoming.closest("section");
    if (!section) throw new Error("no section");
    expect(within(section).getByText(/Ana · 2 marks to photograph/)).toBeInTheDocument();
  });

  it("counts days to an appointment in whole local days", () => {
    expect(daysUntil("2026-10-20", new Date(2026, 9, 1, 23, 30))).toBe(19);
    expect(daysUntil("2026-09-30", new Date(2026, 9, 1, 0, 5))).toBe(-1);
  });
});
