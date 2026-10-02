import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "@/app/App";
import i18n from "@/lib/i18n";
import { installMockApi } from "./mockApi";

const SESSION = { username: "jose", language: "en", theme: "system" };
const PUBLIC_KEY = "BP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A8";

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

/** What a browser hands out: a push manager that remembers one subscription for this device. */
function fakeBrowser() {
  let subscription: { endpoint: string; toJSON: () => object; unsubscribe: () => Promise<boolean> } | null =
    null;
  const pushManager = {
    getSubscription: async () => subscription,
    subscribe: async (options: { applicationServerKey: Uint8Array }) => {
      expect(options.applicationServerKey).toHaveLength(65);
      subscription = {
        endpoint: "https://push.example.net/send/device-1",
        toJSON: () => ({
          endpoint: "https://push.example.net/send/device-1",
          keys: { p256dh: PUBLIC_KEY, auth: "BTBZMqHH6r4Tts7J_aSIgg" },
        }),
        unsubscribe: async () => {
          subscription = null;
          return true;
        },
      };
      return subscription;
    },
  };
  const registration = { pushManager };
  Object.defineProperty(navigator, "serviceWorker", {
    value: { ready: Promise.resolve(registration), getRegistration: async () => registration },
    configurable: true,
  });
  vi.stubGlobal("isSecureContext", true);
  vi.stubGlobal("PushManager", function PushManager() {});
  vi.stubGlobal("Notification", { requestPermission: async () => "granted" });
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
});
afterEach(() => {
  vi.unstubAllGlobals();
  Reflect.deleteProperty(navigator, "serviceWorker");
});

describe("notifications on this device", () => {
  it("stays out of the way when the server has them off", async () => {
    fakeBrowser();
    installMockApi({ claimed: true, session: SESSION });
    renderApp("/settings");
    expect(await screen.findByRole("heading", { name: "Reminders" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /Notifications on this device/ })).not.toBeInTheDocument();
  });

  it("subscribes this device with the server's key, sends a test, and unsubscribes", async () => {
    fakeBrowser();
    const state = installMockApi({
      claimed: true,
      session: SESSION,
      push: { enabled: true, public_key: PUBLIC_KEY, subscriptions: 0 },
    });
    renderApp("/settings");
    const user = userEvent.setup();
    expect(await screen.findByText("This device does not receive them yet.")).toBeInTheDocument();
    expect(screen.getByText("No device of yours is subscribed yet.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Turn on for this device" }));
    expect(await screen.findByText("This device receives them.")).toBeInTheDocument();
    const posted = state.calls.find((c) => c.method === "POST" && c.url.endsWith("/api/push/subscriptions"));
    expect(posted?.body).toEqual({
      endpoint: "https://push.example.net/send/device-1",
      keys: { p256dh: PUBLIC_KEY, auth: "BTBZMqHH6r4Tts7J_aSIgg" },
    });
    expect(screen.getByText("1 device of yours subscribed.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Send a test notification" }));
    expect(await screen.findByText("Sent to 1, failed for 0.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Turn off for this device" }));
    await waitFor(() => expect(state.push.subscriptions).toBe(0));
    expect(await screen.findByText("This device does not receive them yet.")).toBeInTheDocument();
  });
});
