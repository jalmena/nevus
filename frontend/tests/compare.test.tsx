import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "@/app/App";
import { niceTicks, yDomain } from "@/features/measure/SizeChart";
import { scaleBarMm } from "@/lib/comparisons";
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
const VISITS = [
  {
    id: "o1",
    lesion_id: "l1",
    captured_at: "2026-03-02T10:00:00Z",
    notes: null,
    symptoms: [],
    images: ["i1"],
  },
  {
    id: "o2",
    lesion_id: "l1",
    captured_at: "2026-09-01T10:00:00Z",
    notes: null,
    symptoms: [],
    images: ["i2"],
  },
];
const MEASUREMENTS = [
  { id: "m1", observation_id: "o1", image_id: "i1", longest_mm: 5.1, captured_at: "2026-03-02T10:00:00Z" },
  { id: "m2", observation_id: "o2", image_id: "i2", longest_mm: 5.4, captured_at: "2026-09-01T10:00:00Z" },
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
    lesions: [LESION],
    observations: VISITS,
    measurements: MEASUREMENTS,
    ...extra,
  });
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
});
afterEach(() => vi.unstubAllGlobals());

describe("size over time", () => {
  it("draws the longest diameter with its uncertainty and walks through the visits by keyboard", async () => {
    install();
    renderApp("/lesions/l1");
    expect(await screen.findByRole("heading", { name: "Size over time" })).toBeInTheDocument();
    expect(screen.getByText(/The shaded band is the measurement uncertainty/)).toBeInTheDocument();
    const chart = screen.getByRole("slider", { name: /Longest diameter at 2 visits/ });
    expect(chart).toHaveAttribute("aria-valuetext", "Sep 1, 2026: 5.4 ± 0.2 mm");
    const user = userEvent.setup();
    act(() => chart.focus());
    await user.keyboard("{ArrowLeft}");
    expect(chart).toHaveAttribute("aria-valuetext", "Mar 2, 2026: 5.1 ± 0.2 mm");
    expect(chart).toHaveAttribute("aria-valuenow", "1");
    await user.keyboard("{End}");
    expect(chart).toHaveAttribute("aria-valuenow", "2");
  });

  it("shows the area too, in square millimetres", async () => {
    install();
    renderApp("/lesions/l1");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("radio", { name: "Area" }));
    const chart = screen.getByRole("slider", { name: /Area at 2 visits/ });
    expect(chart).toHaveAttribute("aria-valuetext", "Sep 1, 2026: 19.6 ± 1.5 mm²");
  });

  it("offers the same numbers as a table and as a CSV download", async () => {
    install();
    renderApp("/lesions/l1");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Show as a table" }));
    const table = screen.getByRole("table");
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(3);
    expect(within(rows[1] as HTMLElement).getByText("5.1 ± 0.2 mm")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download as CSV" })).toHaveAttribute(
      "href",
      "/api/lesions/l1/measurements.csv",
    );
    await user.click(screen.getByRole("button", { name: "Show as a chart" }));
    expect(screen.getByRole("slider", { name: /Longest diameter/ })).toBeInTheDocument();
  });

  it("leaves out the band and the ± when the person chose not to see uncertainty", async () => {
    install({ session: { ...SESSION, showUncertainty: false } });
    renderApp("/lesions/l1");
    const chart = await screen.findByRole("slider", { name: /Longest diameter/ });
    expect(chart).toHaveAttribute("aria-valuetext", "Sep 1, 2026: 5.4 mm");
    expect(screen.getByText("At each visit.")).toBeInTheDocument();
  });

  it("keeps small differences from looking like a slope", () => {
    const [lo, hi] = yDomain(
      [
        { value: 5.1, sigma: 0.2 },
        { value: 5.3, sigma: 0.2 },
      ],
      2,
    );
    expect(hi - lo).toBeGreaterThanOrEqual(2);
    const { ticks } = niceTicks(lo, hi);
    expect(ticks.length).toBeGreaterThanOrEqual(3);
    expect(ticks.length).toBeLessThanOrEqual(6);
    expect(yDomain([{ value: 0.5, sigma: 0.3 }])[0]).toBe(0);
  });
});

describe("comparing two visits", () => {
  it("lines the photos up with the card and offers four views, the difference one with its caveat", async () => {
    const state = install();
    renderApp("/lesions/l1/compare");
    expect(await screen.findByText("Lined up with the reference card in both photos.")).toBeInTheDocument();
    const call = state.calls.find((c) => c.url.endsWith("/api/comparisons"));
    expect(call?.body).toEqual({ image_a: "i1", image_b: "i2" });
    const views = screen.getByRole("radiogroup", { name: "View" });
    const user = userEvent.setup();
    const side = within(views).getByRole("radio", { name: "Side by side" });
    expect(side).toHaveAttribute("aria-checked", "true");
    expect(screen.getAllByRole("application")).toHaveLength(2);
    side.focus();
    await user.keyboard("{ArrowRight}");
    expect(within(views).getByRole("radio", { name: "On top" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("slider", { name: "How much of the later photo shows" })).toBeInTheDocument();
    await user.click(within(views).getByRole("radio", { name: "Differences" }));
    expect(screen.getByText(/measures nothing/)).toBeInTheDocument();
    expect(screen.getAllByRole("application")).toHaveLength(1);
  });

  it("says why the photos could not be lined up and keeps them side by side", async () => {
    install({ comparison: { status: "abstained", reason: "distance" } });
    renderApp("/lesions/l1/compare?mode=overlay");
    expect(await screen.findByText(/They were taken from very different distances\./)).toBeInTheDocument();
    expect(screen.queryByRole("radiogroup", { name: "View" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("application")).toHaveLength(2);
  });

  it("links to the comparison from the mark once two visits have photos", async () => {
    install();
    renderApp("/lesions/l1");
    expect(await screen.findByRole("link", { name: "Compare visits" })).toHaveAttribute(
      "href",
      "/lesions/l1/compare",
    );
  });

  it("picks a scale bar that fits the zoom", () => {
    expect(scaleBarMm(0.05)).toBe(5);
    expect(scaleBarMm(0.01)).toBe(1);
    expect(scaleBarMm(1)).toBe(50);
  });
});

describe("photo pickers", () => {
  it("compares whichever photos are chosen", async () => {
    const state = install({
      observations: [
        ...VISITS,
        {
          id: "o3",
          lesion_id: "l1",
          captured_at: "2026-06-01T10:00:00Z",
          notes: null,
          symptoms: [],
          images: ["i3"],
        },
      ],
    });
    renderApp("/lesions/l1/compare");
    const user = userEvent.setup();
    const earlier = await screen.findByRole("combobox", { name: "Earlier" });
    await user.selectOptions(earlier, "i3");
    await waitFor(() =>
      expect(
        state.calls.some(
          (c) =>
            c.url.endsWith("/api/comparisons") &&
            JSON.stringify(c.body) === JSON.stringify({ image_a: "i3", image_b: "i2" }),
        ),
      ).toBe(true),
    );
  });
});
