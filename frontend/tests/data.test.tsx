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

describe("trash", () => {
  it("restores an item, and deleting for good asks for the password first", async () => {
    const state = installMockApi({
      claimed: true,
      session: SESSION,
      persons: [PERSON],
      trash: [
        { kind: "lesion", id: "t1", label: "Chest", person_id: PERSON.id, person_name: "Ana" },
        { kind: "image", id: "t2", label: "Chest · close_up", person_id: PERSON.id, person_name: "Ana" },
      ],
    });
    await i18n.changeLanguage("en");
    renderApp("/trash");
    const user = userEvent.setup();
    const [firstRestore] = await screen.findAllByRole("button", { name: "Restore" });
    if (!firstRestore) throw new Error("no restore button");
    await user.click(firstRestore);
    await waitFor(() => expect(state.trash.map((t) => t.id)).toEqual(["t2"]));

    await user.click(await screen.findByRole("button", { name: "Delete now" }));
    expect(await screen.findByRole("heading", { name: "Confirm it is you" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("Password"), "correct horse battery");
    await user.click(screen.getByRole("button", { name: "Confirm" }));
    await waitFor(() => expect(state.trash).toEqual([]));
    expect(await screen.findByRole("heading", { name: "The trash is empty" })).toBeInTheDocument();
  });
});

describe("exports", () => {
  it("exports a person with a passphrase after confirming the password", async () => {
    const state = installMockApi({ claimed: true, session: SESSION, persons: [PERSON] });
    await i18n.changeLanguage("en");
    renderApp(`/persons/${PERSON.id}`);
    const user = userEvent.setup();
    expect(await screen.findByText("3 photos, 4.5 MB")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Export this person" }));
    await user.type(screen.getByLabelText("Passphrase"), "a long passphrase");
    await user.type(screen.getByLabelText("Repeat the passphrase"), "a long passphrase");
    await user.click(screen.getByRole("button", { name: "Start the export" }));
    await user.type(await screen.findByLabelText("Password"), "correct horse battery");
    await user.click(screen.getByRole("button", { name: "Confirm" }));
    await waitFor(() => expect(state.exports).toHaveLength(1));
    expect(await screen.findByText(/The export is being prepared/)).toBeInTheDocument();
  });

  it("refuses to delete a profile until its name is typed", async () => {
    installMockApi({ claimed: true, session: SESSION, persons: [PERSON] });
    await i18n.changeLanguage("en");
    renderApp(`/persons/${PERSON.id}`);
    const button = await screen.findByRole("button", { name: "Delete for good" });
    expect(button).toBeDisabled();
    await userEvent.setup().type(screen.getByLabelText("Type Ana to confirm"), "Ana");
    expect(button).toBeEnabled();
  });
});
