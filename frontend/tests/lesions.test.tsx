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

describe("marks on the body map", () => {
  it("places a mark by tapping the map and lands on its page", async () => {
    const state = installMockApi({ claimed: true, session: SESSION, persons: [PERSON] });
    await i18n.changeLanguage("en");
    renderApp(`/persons/${PERSON.id}`);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Add a mark" }));
    expect(screen.getByRole("status")).toHaveTextContent("Tap the zone where the mark is");
    await user.click(screen.getByRole("button", { name: "Right pectoral" })); // zooms in on the zone
    await user.click(screen.getByRole("button", { name: "Right pectoral" })); // places the mark
    await user.type(screen.getByLabelText("Name"), "Chest mark");
    await user.click(screen.getByRole("button", { name: "Create the mark" }));
    expect(await screen.findByRole("heading", { name: "Chest mark" })).toBeInTheDocument();
    expect(state.lesions).toHaveLength(1);
    expect(state.lesions[0]?.zone).toBe("1250");
    expect(state.lesions[0]?.x).toBeGreaterThan(0);
    expect(screen.getByText(/Right pectoral · Front/)).toBeInTheDocument();
  });

  it("uses the zone already selected when a mark is added, and clears the selection on a second tap", async () => {
    installMockApi({ claimed: true, session: SESSION, persons: [PERSON] });
    await i18n.changeLanguage("en");
    renderApp(`/persons/${PERSON.id}`);
    const user = userEvent.setup();
    const zone = await screen.findByRole("button", { name: "Right pectoral" });
    await user.click(zone);
    expect(screen.getByRole("status")).toHaveTextContent("Right pectoral · Front");
    await user.click(zone); // the same zone again: deselected
    expect(screen.getByRole("status")).toHaveTextContent("Tap a zone to select it.");
    await user.click(zone);
    await user.click(screen.getByRole("group", { name: /Body map/ })); // outside the body: deselected
    expect(screen.getByRole("status")).toHaveTextContent("Tap a zone to select it.");

    await user.click(zone);
    const map = screen.getByRole("group", { name: /Body map/ });
    const before = map.getAttribute("viewBox");
    await user.click(screen.getByRole("button", { name: "Add a mark" }));
    expect(screen.getByRole("status")).toHaveTextContent("Tap the exact spot of the mark in Right pectoral.");
    expect(map.getAttribute("viewBox")).not.toBe(before); // zoomed in on the selected zone already
    await user.click(zone); // one tap places the mark
    expect(await screen.findByLabelText("Name")).toBeInTheDocument();
  });

  it("moves a mark to the trash from its page", async () => {
    const state = installMockApi({
      claimed: true,
      session: SESSION,
      persons: [PERSON],
      lesions: [
        { id: "l1", person_id: PERSON.id, label: "Shoulder mark", zone: "1650", x: 0.3, y: 0.2, due: false },
      ],
    });
    await i18n.changeLanguage("en");
    renderApp("/lesions/l1");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Move the mark to the trash" }));
    expect(await screen.findByRole("heading", { name: "Ana" })).toBeInTheDocument();
    expect(state.lesions).toHaveLength(0);
    expect(screen.queryByRole("button", { name: "Shoulder mark" })).not.toBeInTheDocument();
  });

  it("shows existing marks as markers and in the list, with the due ones flagged", async () => {
    installMockApi({
      claimed: true,
      session: SESSION,
      persons: [PERSON],
      lesions: [
        { id: "l1", person_id: PERSON.id, label: "Shoulder mark", zone: "1650", x: 0.3, y: 0.2, due: true },
        { id: "l2", person_id: PERSON.id, label: null, zone: "2350", x: 0.4, y: 0.5, due: false },
      ],
    });
    await i18n.changeLanguage("en");
    renderApp(`/persons/${PERSON.id}`);
    expect(await screen.findByRole("button", { name: "Shoulder mark" })).toBeInTheDocument();
    expect(screen.getByText("Due")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Left buttock" })).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("radio", { name: "Back" }));
    expect(await screen.findAllByRole("button", { name: "Left buttock" })).toHaveLength(2);
  });
});

describe("visits", () => {
  it("creates a visit from the mark page, uploads a photo and saves notes", async () => {
    const state = installMockApi({
      claimed: true,
      session: SESSION,
      persons: [PERSON],
      lesions: [
        { id: "l1", person_id: PERSON.id, label: "Chest mark", zone: "1250", x: 0.4, y: 0.25, due: false },
      ],
    });
    await i18n.changeLanguage("en");
    renderApp("/lesions/l1");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "New visit" }));
    expect(await screen.findByRole("heading", { name: "Photos" })).toBeInTheDocument();
    expect(state.observations).toHaveLength(1);

    const file = new File([new Uint8Array([0xff, 0xd8, 0xff, 0xd9])], "photo.jpg", { type: "image/jpeg" });
    await user.upload(screen.getByLabelText("Take a photo"), file);
    await waitFor(() => expect(state.observations[0]?.images).toHaveLength(1));
    expect(await screen.findByRole("button", { name: "Open the photo" })).toBeInTheDocument();

    await user.click(screen.getByLabelText("Itching"));
    await user.type(screen.getByLabelText("Notes"), "Looks the same to me.");
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(state.observations[0]?.notes).toBe("Looks the same to me."));
    expect(state.observations[0]?.symptoms).toEqual(["itching"]);
  });

  it("lists visits on the mark page newest first with their photos and symptoms", async () => {
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
          captured_at: "2026-06-01T10:00:00Z",
          notes: "First look",
          symptoms: [],
          images: [],
        },
        {
          id: "o2",
          lesion_id: "l1",
          captured_at: "2026-09-01T10:00:00Z",
          notes: null,
          symptoms: ["pain"],
          images: ["i1"],
        },
      ],
    });
    await i18n.changeLanguage("en");
    renderApp("/lesions/l1");
    const items = await screen.findAllByRole("listitem");
    expect(items[0]).toHaveTextContent("1 photo");
    expect(items[0]).toHaveTextContent("Pain");
    expect(items[1]).toHaveTextContent("First look");
  });
});

describe("quality warnings", () => {
  it("shows what was found and how to retake, without blocking the visit", async () => {
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
      flagged: ["i1"],
    });
    await i18n.changeLanguage("en");
    renderApp("/observations/o1");
    expect(await screen.findByText("Saved with quality warnings")).toBeInTheDocument();
    expect(screen.getByText(/hold the phone steady/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open the photo (has quality warnings)" })).toBeInTheDocument();
  });
});
