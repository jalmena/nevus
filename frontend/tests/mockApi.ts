/** A tiny in-memory backend for component tests, speaking the same JSON as the real API. */
import { vi } from "vitest";

export interface MockState {
  claimed: boolean;
  session: { username: string; language: string; theme: string } | null;
  persons: { id: string; display_name: string }[];
  calls: { method: string; url: string; body?: unknown }[];
}

const user = (username: string, language = "en", theme = "system") => ({
  id: "0199a000-0000-7000-8000-000000000001",
  username,
  email: null,
  role: "admin",
  language,
  theme,
  show_uncertainty: true,
  created_at: "2026-09-23T10:00:00Z",
  last_login_at: null,
  disabled_at: null,
});

export function installMockApi(initial: Partial<MockState> = {}): MockState {
  const state: MockState = { claimed: false, session: null, persons: [], calls: [], ...initial };
  const json = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const request =
        input instanceof Request ? input : new Request(new URL(String(input), window.location.origin), init);
      const url = request.url;
      const method = request.method;
      const text = method === "GET" || method === "HEAD" ? "" : await request.text();
      const body = text ? (JSON.parse(text) as unknown) : undefined;
      state.calls.push({ method, url, body });
      const path = url.replace(/^https?:\/\/[^/]+/, "");
      if (path === "/api/auth/instance") return json({ claimed: state.claimed, version: "test" });
      if (path === "/api/auth/session") {
        return state.session
          ? json({
              user: user(state.session.username, state.session.language, state.session.theme),
              sudo_until: null,
            })
          : json({ detail: "Sign in to continue." }, 401);
      }
      if (path === "/api/auth/claim" && method === "POST") {
        const creds = body as { username: string; password: string };
        state.claimed = true;
        state.session = { username: creds.username.toLowerCase(), language: "en", theme: "system" };
        return json({ user: user(state.session.username), sudo_until: null }, 201);
      }
      if (path === "/api/auth/login" && method === "POST") {
        const creds = body as { username: string; password: string };
        if (creds.password !== "correct horse battery")
          return json({ detail: "Wrong username or password." }, 401);
        state.session = { username: creds.username.toLowerCase(), language: "en", theme: "system" };
        return json({ user: user(state.session.username), sudo_until: null });
      }
      if (path === "/api/auth/logout") {
        state.session = null;
        return new Response(null, { status: 204 });
      }
      if (path === "/api/auth/me" && method === "PATCH") {
        const patch = body as { language?: string; theme?: string };
        if (state.session) {
          state.session.language = patch.language ?? state.session.language;
          state.session.theme = patch.theme ?? state.session.theme;
          return json(user(state.session.username, state.session.language, state.session.theme));
        }
      }
      if (path === "/api/persons" && method === "GET") {
        return json(
          state.persons.map((p) => ({
            ...p,
            birth_year: null,
            skin_tone: null,
            owner_user_id: "0199a000-0000-7000-8000-000000000001",
            experimental_analysis: false,
            created_at: "2026-09-23T10:00:00Z",
            updated_at: "2026-09-23T10:00:00Z",
            my_role: "owner",
          })),
        );
      }
      if (path === "/api/persons" && method === "POST") {
        const person = body as { display_name: string };
        const created = {
          id: `0199a000-0000-7000-8000-00000000000${state.persons.length + 2}`,
          display_name: person.display_name,
        };
        state.persons.push(created);
        return json(
          {
            ...created,
            birth_year: null,
            skin_tone: null,
            owner_user_id: "x",
            experimental_analysis: false,
            created_at: "",
            updated_at: "",
            my_role: "owner",
          },
          201,
        );
      }
      return json({ detail: `unmocked ${method} ${path}` }, 404);
    }),
  );
  return state;
}
