import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "@/app/App";
import i18n from "@/lib/i18n";
import { installMockApi, PROTOCOL, type MockBodySession, type MockState } from "./mockApi";

const PERSON = { id: "0199a000-0000-7000-8000-000000000002", display_name: "Ana" };
const SESSION = { username: "jose", language: "en", theme: "system" };
const LESIONS = [
  { id: "l1", person_id: PERSON.id, label: "Chest mark", zone: "1250", x: 0.4, y: 0.25, due: false },
  { id: "l2", person_id: PERSON.id, label: "Back mark", zone: "2250", x: 0.5, y: 0.3, due: false },
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
  return installMockApi({ claimed: true, session: SESSION, persons: [PERSON], lesions: LESIONS, ...extra });
}

function session(id: string, startedAt: string, zones: MockBodySession["zones"] = {}): MockBodySession {
  return { id, person_id: PERSON.id, status: "open", started_at: startedAt, zones };
}

const photo = () => new File(["zone"], "zone.jpg", { type: "image/jpeg" });

beforeEach(async () => {
  await i18n.changeLanguage("en");
});
afterEach(() => vi.unstubAllGlobals());

describe("full-body sessions", () => {
  it("starts from the person's page and lists every region in the protocol's order", async () => {
    const state = install();
    renderApp(`/persons/${PERSON.id}`);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Start a session" }));
    expect(await screen.findByRole("heading", { level: 1, name: /^Session of/ })).toBeInTheDocument();
    const regions = screen.getAllByRole("heading", { level: 2 });
    expect(regions).toHaveLength(PROTOCOL.length);
    expect(regions[0]).toHaveTextContent("Face");
    expect(regions.at(-1)).toHaveTextContent("Soles");
    expect(screen.getByText(/0 of 18 regions photographed/)).toBeInTheDocument();
    expect(screen.getAllByText(/may include intimate areas/)).toHaveLength(2);
    expect(
      state.calls.some((c) => c.method === "POST" && c.url.endsWith(`/api/persons/${PERSON.id}/sessions`)),
    ).toBe(true);
  });

  it("photographs a region, skips another and takes the skip back", async () => {
    const state = install({ bodySessions: [session("s1", "2026-10-01T10:00:00Z")] });
    renderApp("/sessions/s1");
    const user = userEvent.setup();
    const chest = (await screen.findByRole("heading", { name: "Chest and shoulders" })).closest("li");
    if (!chest) throw new Error("no chest region");
    await user.upload(within(chest).getByLabelText("Take the photo"), photo());
    expect(await within(chest).findByText("0 marks")).toBeInTheDocument();
    expect(
      within(chest).getByRole("link", { name: "Open the photo of Chest and shoulders" }),
    ).toHaveAttribute("href", "/sessions/s1/zones/chest");
    expect(within(chest).queryByRole("button", { name: "Skip" })).not.toBeInTheDocument();

    const abdomen = screen.getByRole("heading", { name: "Abdomen and pelvis" }).closest("li");
    if (!abdomen) throw new Error("no abdomen region");
    await user.click(within(abdomen).getByRole("button", { name: "Skip" }));
    expect(await within(abdomen).findByText("Skipped")).toBeInTheDocument();
    await user.click(within(abdomen).getByRole("button", { name: "Photograph it after all" }));
    expect(await within(abdomen).findByText("Not photographed yet")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Finish the session" }));
    expect(await screen.findByText(/^Finished/)).toBeInTheDocument();
    expect(state.bodySessions[0]?.status).toBe("finished");
  });

  it("links a tapped mark to one already followed, or records a new one in a zone the photo shows", async () => {
    const state = install({
      bodySessions: [
        session("s1", "2026-10-01T10:00:00Z", { chest: { status: "captured", image_id: "img1", marks: [] } }),
      ],
    });
    renderApp("/sessions/s1/zones/chest");
    const user = userEvent.setup();
    const canvas = await screen.findByRole("application", { name: "Photo of Chest and shoulders" });
    canvas.focus();
    await user.keyboard("{Enter}");
    const chooser = await screen.findByRole("region", { name: "The mark you tapped" });
    // Marks of the zones this photo shows come first.
    expect(within(chooser).getByLabelText("A mark you follow")).toHaveValue("l1");
    await user.click(within(chooser).getByRole("button", { name: "Link to it" }));
    await waitFor(() => expect(state.bodySessions[0]?.zones.chest?.marks).toHaveLength(1));
    const added = state.calls.find((c) => c.method === "POST" && c.url.endsWith("/zones/chest/marks"));
    expect(added?.body).toMatchObject({ x: 0.5, y: 0.5, lesion_id: "l1" });
    expect(await screen.findByRole("button", { name: /1\. Chest mark/ })).toBeInTheDocument();

    canvas.focus();
    await user.keyboard("{Enter}");
    const second = await screen.findByRole("region", { name: "The mark you tapped" });
    const zones = within(second).getByLabelText("Or record a new mark in");
    expect(within(zones).getAllByRole("option")).toHaveLength(
      PROTOCOL.find((z) => z.id === "chest")?.covers.length ?? 0,
    );
    await user.selectOptions(zones, "1251");
    await user.type(within(second).getByLabelText("Name (optional)"), "Left of the sternum");
    await user.click(within(second).getByRole("button", { name: "Record a new mark" }));
    await waitFor(() => expect(state.lesions).toHaveLength(3));
    expect(state.lesions.at(-1)).toMatchObject({ zone: "1251", label: "Left of the sternum" });
  });

  it("offers proposed spots only with the experimental analysis, to confirm or reject", async () => {
    const state = install({ experimental: true, bodySessions: [session("s1", "2026-10-01T10:00:00Z")] });
    renderApp("/sessions/s1");
    const user = userEvent.setup();
    expect(await screen.findByText(/The experimental analysis is on for this person/)).toBeInTheDocument();
    const chest = screen.getByRole("heading", { name: "Chest and shoulders" }).closest("li");
    if (!chest) throw new Error("no chest region");
    await user.upload(within(chest).getByLabelText("Take the photo"), photo());
    await user.click(
      await within(chest).findByRole("link", { name: "Open the photo of Chest and shoulders" }),
    );

    await user.click(await screen.findByRole("button", { name: /Proposed: a spot not linked to any mark/ }));
    const panel = screen.getByRole("region", { name: /Proposed spot/ });
    expect(within(panel).getByText("Experimental")).toBeInTheDocument();
    await user.click(within(panel).getByRole("button", { name: "Not a mark" }));
    await waitFor(() =>
      expect(
        state.calls.some((c) => c.method === "PATCH" && (c.body as { state?: string }).state === "rejected"),
      ).toBe(true),
    );
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: /Proposed: a spot/ })).not.toBeInTheDocument(),
    );
  });

  it("blurs areas of the zone photo marked with two taps each, and the photo is replaced", async () => {
    const state = install({
      bodySessions: [
        session("s1", "2026-10-01T10:00:00Z", { chest: { status: "captured", image_id: "img1", marks: [] } }),
      ],
    });
    renderApp("/sessions/s1/zones/chest");
    const user = userEvent.setup();
    const canvas = await screen.findByRole("application", { name: "Photo of Chest and shoulders" });
    await user.click(screen.getByRole("button", { name: "Blur a part of the photo" }));
    expect(screen.getByRole("button", { name: "Blur 0 areas" })).toBeDisabled();
    await user.pointer([{ keys: "[MouseLeft]", target: canvas, coords: { clientX: 64, clientY: 48 } }]);
    await user.pointer([{ keys: "[MouseLeft]", target: canvas, coords: { clientX: 320, clientY: 240 } }]);
    expect(screen.getByRole("button", { name: "Blur 1 area" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Blur 1 area" }));
    await waitFor(() => expect(state.bodySessions[0]?.zones.chest?.image_id).not.toBe("img1"));
    const sent = state.calls.find((c) => c.method === "POST" && c.url.endsWith("/zones/chest/blur"));
    expect(sent?.body).toEqual({ regions: [{ x: 0.1, y: 0.1, width: 0.4, height: 0.4 }] });
    expect(screen.queryByRole("heading", { name: "Blur part of the photo" })).not.toBeInTheDocument();
  });

  it("hides proposed spots when the experimental analysis is off", async () => {
    install({
      bodySessions: [
        session("s1", "2026-10-01T10:00:00Z", {
          chest: {
            status: "captured",
            image_id: "img1",
            marks: [
              {
                id: "m1",
                x: 0.4,
                y: 0.5,
                lesion_id: null,
                source: "candidate",
                state: "pending",
                match: "new",
              },
            ],
          },
        }),
      ],
    });
    renderApp("/sessions/s1/zones/chest");
    expect(
      await screen.findByRole("application", { name: "Photo of Chest and shoulders" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Marks on this photo" })).not.toBeInTheDocument();
  });

  it("compares two sessions region by region, and lists where a mark was seen", async () => {
    const seen = {
      id: "m1",
      x: 0.4,
      y: 0.5,
      lesion_id: "l1",
      source: "person" as const,
      state: "confirmed" as const,
      match: null,
    };
    install({
      bodySessions: [
        session("s2", "2026-10-01T10:00:00Z", {
          chest: { status: "captured", image_id: "img2", marks: [seen] },
          face: { status: "captured", image_id: "img4", marks: [] },
        }),
        session("s1", "2026-04-01T10:00:00Z", {
          chest: { status: "captured", image_id: "img1", marks: [] },
          "upper-back": { status: "captured", image_id: "img3", marks: [] },
        }),
      ],
    });
    const { unmount } = renderApp(`/persons/${PERSON.id}`);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("link", { name: "Compare the last two sessions" }));
    expect(
      await screen.findByRole("heading", { name: "Two sessions, region by region" }),
    ).toBeInTheDocument();
    const region = screen.getByLabelText("Region");
    expect(
      within(region)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["Chest and shoulders"]);
    expect(await screen.findByRole("radiogroup")).toBeInTheDocument();
    unmount();

    renderApp("/lesions/l1");
    const sightings = await screen.findByRole("region", { name: "Seen in full-body sessions" });
    expect(within(sightings).getByRole("link", { name: /Chest and shoulders/ })).toHaveAttribute(
      "href",
      "/sessions/s2/zones/chest",
    );
  });

  it("names the regions and counts in Spanish", async () => {
    await i18n.changeLanguage("es");
    install({
      session: { ...SESSION, language: "es" },
      bodySessions: [
        session("s1", "2026-10-01T10:00:00Z", {
          soles: { status: "skipped", image_id: null, marks: [] },
          face: { status: "skipped", image_id: null, marks: [] },
        }),
      ],
    });
    const { unmount } = renderApp(`/persons/${PERSON.id}`);
    expect(await screen.findByText(/2 saltadas/)).toBeInTheDocument();
    expect(screen.getByText(/0 marcas/)).toBeInTheDocument();
    unmount();
    renderApp("/sessions/s1");
    expect(await screen.findByRole("heading", { name: "Plantas de los pies" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Zona lumbar y glúteos" })).toBeInTheDocument();
  });
});
