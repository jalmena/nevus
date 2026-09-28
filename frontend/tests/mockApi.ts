/** A tiny in-memory backend for component tests, speaking the same JSON as the real API. */
import { vi } from "vitest";

export interface MockLesion {
  id: string;
  person_id: string;
  label: string | null;
  zone: string;
  x: number;
  y: number;
  due: boolean;
}

export interface MockObservation {
  id: string;
  lesion_id: string;
  captured_at: string;
  notes: string | null;
  symptoms: string[];
  images: string[];
}

export interface MockState {
  claimed: boolean;
  session: { username: string; language: string; theme: string } | null;
  persons: { id: string; display_name: string }[];
  lesions: MockLesion[];
  observations: MockObservation[];
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
  const state: MockState = {
    claimed: false,
    session: null,
    persons: [],
    lesions: [],
    observations: [],
    calls: [],
    ...initial,
  };
  const personOut = (p: { id: string; display_name: string }) => ({
    ...p,
    birth_year: null,
    skin_tone: null,
    owner_user_id: "0199a000-0000-7000-8000-000000000001",
    experimental_analysis: false,
    created_at: "2026-09-23T10:00:00Z",
    updated_at: "2026-09-23T10:00:00Z",
    my_role: "owner",
  });
  const view = (zone: string) => (zone.startsWith("2") ? "back" : "front");
  const lesionOut = (l: MockLesion) => {
    const visits = state.observations.filter((o) => o.lesion_id === l.id);
    const last =
      visits
        .map((o) => o.captured_at)
        .sort()
        .at(-1) ?? null;
    return {
      id: l.id,
      person_id: l.person_id,
      type: "mole",
      label: l.label,
      location: {
        zone: l.zone,
        x: l.x,
        y: l.y,
        body_map_version: "nevus-body-map/1",
        view: view(l.zone),
        side: "right",
      },
      first_noticed_on: null,
      status: "active",
      tags: [],
      notes: null,
      interval_days: 90,
      created_at: "2026-09-23T10:00:00Z",
      updated_at: "2026-09-23T10:00:00Z",
      observation_count: visits.length,
      last_observed_at: last,
      next_due_on: "2026-12-31",
      due: l.due,
      latest_image_id: visits.flatMap((o) => o.images).at(-1) ?? null,
    };
  };
  const imageOut = (id: string, observationId: string) => ({
    id,
    person_id: "p",
    observation_id: observationId,
    role: "close_up",
    modality: "camera",
    sha256: "0".repeat(64),
    bytes: 1234,
    mime: "image/jpeg",
    width: 640,
    height: 480,
    orientation: 1,
    source_format: "JPEG",
    re_encoded: false,
    captured_at: "2026-09-12T10:41:07Z",
    created_at: "2026-09-12T10:41:07Z",
    renditions: [{ kind: "thumb", width: 256, height: 192, bytes: 100 }],
  });
  const observationOut = (o: MockObservation) => ({
    id: o.id,
    lesion_id: o.lesion_id,
    captured_at: o.captured_at,
    captured_tz: "Europe/Madrid",
    captured_local_date: o.captured_at.slice(0, 10),
    notes: o.notes,
    symptoms: o.symptoms,
    quality_flags: [],
    created_at: o.captured_at,
    updated_at: o.captured_at,
    images: o.images.map((id) => imageOut(id, o.id)),
  });
  let counter = 100;
  const nextId = () => `0199a000-0000-7000-8000-${String(counter++).padStart(12, "0")}`;
  const json = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const request =
        input instanceof Request ? input : new Request(new URL(String(input), window.location.origin), init);
      const url = request.url;
      const method = request.method;
      // jsdom's FormData is not the one Node's Request understands, so multipart bodies are read from init.
      const form = init?.body instanceof FormData ? init.body : null;
      const text = method === "GET" || method === "HEAD" || form ? "" : await request.text();
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
        return json(state.persons.map(personOut));
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
      let match = /^\/api\/persons\/([^/]+)$/.exec(path);
      if (match && method === "GET") {
        const found = state.persons.find((p) => p.id === match?.[1]);
        return found ? json(personOut(found)) : json({ detail: "No such person." }, 404);
      }
      match = /^\/api\/persons\/([^/]+)\/lesions$/.exec(path);
      if (match && method === "GET") {
        return json(state.lesions.filter((l) => l.person_id === match?.[1]).map(lesionOut));
      }
      if (match && method === "POST") {
        const input = body as { label: string | null; location: { zone: string; x: number; y: number } };
        const created: MockLesion = {
          id: nextId(),
          person_id: match[1] ?? "",
          label: input.label,
          zone: input.location.zone,
          x: input.location.x,
          y: input.location.y,
          due: false,
        };
        state.lesions.push(created);
        return json(lesionOut(created), 201);
      }
      match = /^\/api\/lesions\/([^/]+)$/.exec(path);
      if (match) {
        const found = state.lesions.find((l) => l.id === match?.[1]);
        if (!found) return json({ detail: "No such lesion." }, 404);
        if (method === "PATCH") {
          const patch = body as { label?: string | null };
          if (patch.label !== undefined) found.label = patch.label;
        }
        return json(lesionOut(found));
      }
      match = /^\/api\/lesions\/([^/]+)\/observations$/.exec(path);
      if (match && method === "GET") {
        return json(
          state.observations
            .filter((o) => o.lesion_id === match?.[1])
            .sort((a, b) => b.captured_at.localeCompare(a.captured_at))
            .map(observationOut),
        );
      }
      if (match && method === "POST") {
        const created: MockObservation = {
          id: nextId(),
          lesion_id: match[1] ?? "",
          captured_at: "2026-09-28T09:00:00Z",
          notes: null,
          symptoms: [],
          images: [],
        };
        state.observations.push(created);
        return json(observationOut(created), 201);
      }
      match = /^\/api\/observations\/([^/]+)$/.exec(path);
      if (match) {
        const found = state.observations.find((o) => o.id === match?.[1]);
        if (!found) return json({ detail: "No such observation." }, 404);
        if (method === "DELETE") {
          state.observations = state.observations.filter((o) => o.id !== found.id);
          return new Response(null, { status: 204 });
        }
        if (method === "PATCH") {
          const patch = body as { notes?: string | null; symptoms?: string[] };
          if (patch.notes !== undefined) found.notes = patch.notes;
          if (patch.symptoms !== undefined) found.symptoms = patch.symptoms;
        }
        return json(observationOut(found));
      }
      match = /^\/api\/observations\/([^/]+)\/images$/.exec(path);
      if (match && method === "POST") {
        const found = state.observations.find((o) => o.id === match?.[1]);
        if (!found) return json({ detail: "No such observation." }, 404);
        const file = form?.get("file");
        if (!(file instanceof File) || file.size === 0) return json({ detail: "The upload is empty." }, 400);
        const id = nextId();
        found.images.push(id);
        return json(imageOut(id, found.id), 201);
      }
      return json({ detail: `unmocked ${method} ${path}` }, 404);
    }),
  );
  return state;
}
