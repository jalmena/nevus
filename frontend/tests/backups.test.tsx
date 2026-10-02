import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "@/app/App";
import i18n from "@/lib/i18n";
import { installMockApi, type MockState } from "./mockApi";

const SESSION = { username: "jose", language: "en", theme: "system" };
const FAILING: MockState["backups"] = {
  enabled: true,
  backup_hour: 3,
  verify_days: 7,
  count: 1,
  latest: { file: "nevus-backup-20261002T030000Z.tar.age", bytes: 1000, created_at: "2026-10-02T03:00:00Z" },
  verification: {
    ok: false,
    checked_at: "2026-10-02T04:00:00Z",
    archive: "nevus-backup-20261002T030000Z.tar.age",
    blobs_in_archive: 3,
    problems: ["damaged_blobs", "unreadable: RestoreError: not a neVus backup"],
  },
  backup_queued: false,
  verification_queued: false,
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

describe("backups in the settings", () => {
  it("shows the latest backup and its read-back, and starts a backup or a read-back on demand", async () => {
    const state = installMockApi({ claimed: true, session: SESSION });
    renderApp("/settings");
    const user = userEvent.setup();
    expect(await screen.findByRole("heading", { name: "Backups (administrator)" })).toBeInTheDocument();
    expect(screen.getByText(/3 backups, the latest from/)).toBeInTheDocument();
    expect(screen.getByText(/would restore \(412 files checked\)/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Read the latest backup back now" }));
    await waitFor(() => expect(state.backups.verification_queued).toBe(true));
    expect(await screen.findByRole("button", { name: "Reading it back…" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Back up now" }));
    await waitFor(() => expect(state.backups.backup_queued).toBe(true));
    expect(
      state.calls.filter((c) => c.method === "POST" && c.url.includes("/api/admin/backups/")),
    ).toHaveLength(2);
  });

  it("lists the problems of a backup that would not restore, and says how to turn backups on", async () => {
    installMockApi({ claimed: true, session: SESSION, backups: FAILING });
    const first = renderApp("/settings");
    const alerts = await screen.findAllByRole("alert");
    const alert = alerts.find((item) => item.textContent?.includes("has problems"));
    if (!alert) throw new Error("no verification notice");
    const items = within(alert).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("do not match their checksums");
    expect(items[1]).toHaveTextContent("could not be read");
    first.unmount();
    vi.unstubAllGlobals();

    installMockApi({ claimed: true, session: SESSION, backups: { ...FAILING, enabled: false } });
    renderApp("/settings");
    expect(await screen.findByText(/Nightly backups are off/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Back up now" })).not.toBeInTheDocument();
  });
});
