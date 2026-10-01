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
  snoozed_until?: string | null;
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
  session: {
    username: string;
    language: string;
    theme: string;
    role?: string;
    email?: string | null;
    showUncertainty?: boolean;
  } | null;
  persons: { id: string; display_name: string }[];
  lesions: MockLesion[];
  observations: MockObservation[];
  /** Image ids whose quality check found a warning. */
  flagged: string[];
  measurements: {
    id: string;
    observation_id: string;
    image_id: string;
    longest_mm: number;
    captured_at?: string;
  }[];
  /** What aligning two photos gives: lined up (with the card) or refused for a reason. */
  comparison: { status: "aligned" } | { status: "abstained"; reason: string };
  appointments: {
    id: string;
    person_id: string;
    date: string;
    notes: string | null;
    report_id: string | null;
    created_at: string;
  }[];
  /** Reports; a queued one is ready the next time the list is read, unless it is set to fail. */
  reports: {
    id: string;
    scope: string;
    lesion_ids: string[];
    language: string;
    paper: string;
    status: string;
    fail?: boolean;
  }[];
  trash: { kind: string; id: string; label: string; person_id: string; person_name: string }[];
  exports: { id: string; status: string }[];
  sudo: boolean;
  calls: { method: string; url: string; body?: unknown }[];
}

const user = (
  username: string,
  language = "en",
  theme = "system",
  role = "admin",
  email: string | null = null,
  showUncertainty = true,
) => ({
  id: "0199a000-0000-7000-8000-000000000001",
  username,
  email,
  role,
  card_line_mm: null,
  email_reminders: false,
  language,
  theme,
  show_uncertainty: showUncertainty,
  created_at: "2026-09-23T10:00:00Z",
  last_login_at: null,
  disabled_at: null,
});

const PERSON_ID = "0199a000-0000-7000-8000-000000000002";

export function installMockApi(initial: Partial<MockState> = {}): MockState {
  const state: MockState = {
    claimed: false,
    session: null,
    persons: [],
    lesions: [],
    observations: [],
    flagged: [],
    measurements: [],
    trash: [],
    exports: [],
    sudo: false,
    calls: [],
    comparison: { status: "aligned" },
    reports: [],
    appointments: [],
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
      due: l.due && !l.snoozed_until,
      snoozed_until: l.snoozed_until ?? null,
      latest_image_id: visits.flatMap((o) => o.images).at(-1) ?? null,
      latest_measurement: null,
      measurement_change: null,
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
    quality_flags: state.flagged.includes(id) ? ["blurry"] : [],
    quality_checked_at: "2026-09-12T10:41:08Z",
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
    quality_flags: o.images.some((id) => state.flagged.includes(id)) ? ["blurry"] : [],
    created_at: o.captured_at,
    updated_at: o.captured_at,
    images: o.images.map((id) => imageOut(id, o.id)),
  });
  const measurementOut = (m: {
    id: string;
    observation_id: string;
    image_id: string;
    longest_mm: number;
    captured_at?: string;
  }) => ({
    id: m.id,
    observation_id: m.observation_id,
    lesion_id: "l1",
    image_id: m.image_id,
    scale_reference_id: "ref-card",
    scale_kind: "card",
    method: "assisted",
    shape: {},
    longest_mm: m.longest_mm,
    perpendicular_mm: 4.9,
    area_mm2: 19.6,
    sigma_longest_mm: 0.2,
    sigma_perpendicular_mm: 0.2,
    sigma_area_mm2: 1.5,
    tilt_deg: 4,
    flags: [],
    captured_at: m.captured_at ?? "2026-09-01T10:00:00Z",
    created_at: m.captured_at ?? "2026-09-01T10:00:00Z",
    change: null,
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
              user: user(
                state.session.username,
                state.session.language,
                state.session.theme,
                state.session.role ?? "admin",
                state.session.email ?? null,
                state.session.showUncertainty ?? true,
              ),
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
      let match: RegExpExecArray | null = /^\/api\/persons\/([^/]+)$/.exec(path);
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
      const needSudo = () =>
        new Response(JSON.stringify({ detail: "Confirm your password to continue." }), {
          status: 403,
          headers: { "content-type": "application/json", "x-sudo-required": "1" },
        });
      if (path === "/api/auth/sudo" && method === "POST") {
        const given = body as { password: string };
        if (given.password !== "correct horse battery") return json({ detail: "Wrong password." }, 401);
        state.sudo = true;
        return json({ user: user(state.session?.username ?? "jose"), sudo_until: "2026-10-01T10:05:00Z" });
      }
      if (path === "/api/trash" && method === "GET") {
        return json(
          state.trash.map((item) => ({
            ...item,
            deleted_at: "2026-09-30T10:00:00Z",
            purge_after: "2026-10-30T10:00:00Z",
          })),
        );
      }
      match = /^\/api\/trash\/([^/]+)\/([^/]+)(\/restore)?$/.exec(path);
      if (match) {
        if (!match[3] && !state.sudo) return needSudo();
        state.trash = state.trash.filter((item) => item.id !== match?.[2]);
        return new Response(null, { status: 204 });
      }
      if (path === "/api/exports" && method === "POST") {
        if (!state.sudo) return needSudo();
        const created = { id: nextId(), status: "ready" };
        state.exports.push(created);
        return json(
          {
            ...created,
            person_id: null,
            file_name: "nevus-export.zip.age",
            bytes: 2048,
            error: null,
            created_at: "2026-10-01T10:00:00Z",
            expires_at: "2026-10-08T10:00:00Z",
          },
          202,
        );
      }
      if (path === "/api/exports" && method === "GET") {
        return json(
          state.exports.map((e) => ({
            ...e,
            person_id: null,
            file_name: "nevus-export.zip.age",
            bytes: 2048,
            error: null,
            created_at: "2026-10-01T10:00:00Z",
            expires_at: "2026-10-08T10:00:00Z",
          })),
        );
      }
      match = /^\/api\/persons\/([^/]+)\/usage$/.exec(path);
      if (match) return json({ images: 3, bytes: 4_500_000, quota_bytes: null, over_quota: false });
      if (path === "/api/due") {
        return json(
          state.lesions
            .filter((l) => l.due && !l.snoozed_until)
            .map((l) => ({
              lesion_id: l.id,
              label: l.label,
              zone: l.zone,
              person_id: l.person_id,
              person_name: state.persons.find((p) => p.id === l.person_id)?.display_name ?? "",
              next_due_on: "2026-09-20",
              overdue_days: 11,
              last_observed_at: null,
            })),
        );
      }
      match = /^\/api\/lesions\/([^/]+)\/snooze$/.exec(path);
      if (match) {
        const found = state.lesions.find((l) => l.id === match?.[1]);
        if (!found) return json({ detail: "No such lesion." }, 404);
        found.snoozed_until = method === "DELETE" ? null : "2026-10-08";
        return json(lesionOut(found));
      }
      if (path === "/api/admin/email" && method === "GET") {
        return json({
          host: null,
          port: 587,
          security: "starttls",
          username: null,
          has_password: false,
          sender: null,
          public_url: null,
          ready: false,
        });
      }
      if (path === "/api/admin/instance" && method === "GET") return json({ default_language: "en" });
      match = /^\/api\/images\/([^/]+)\/scale$/.exec(path);
      if (match) {
        return json({
          image_id: match[1],
          upright_width: 3000,
          upright_height: 2250,
          card_checked: true,
          card: {
            found: true,
            card: "window",
            tilt_deg: 4,
            mm_per_px: 0.05,
            centre_px: [1500, 1125],
            marker_px: 240,
            flags: [],
          },
          references: [
            {
              id: "ref-card",
              image_id: match[1],
              kind: "card",
              reference_mm: null,
              mm_per_px: 0.05,
              sigma_scale: 0.01,
              tilt_deg: 4,
              geometry: {},
              created_at: "2026-10-01T10:00:00Z",
            },
          ],
          tilt_limit_deg: 15,
        });
      }
      match = /^\/api\/images\/([^/]+)\/fit$/.exec(path);
      if (match && method === "POST") {
        const tap = body as { x: number; y: number };
        const outline = Array.from({ length: 12 }, (_, i) => [
          tap.x + 50 * Math.cos((i / 12) * 2 * Math.PI),
          tap.y + 50 * Math.sin((i / 12) * 2 * Math.PI),
        ]);
        return json({ cx: tap.x, cy: tap.y, r: 50, outline, method: "threshold" });
      }
      match = /^\/api\/observations\/([^/]+)\/measurements\/preview$/.exec(path);
      if (match && method === "POST") {
        return json({
          longest_mm: 5.1,
          perpendicular_mm: 4.9,
          area_mm2: 19.6,
          sigma_longest_mm: 0.2,
          sigma_perpendicular_mm: 0.2,
          sigma_area_mm2: 1.5,
          tilt_deg: 4,
          flags: [],
        });
      }
      match = /^\/api\/observations\/([^/]+)\/measurements$/.exec(path);
      if (match && method === "POST") {
        const input = body as { image_id: string };
        const created = {
          id: nextId(),
          observation_id: match[1] ?? "",
          image_id: input.image_id,
          longest_mm: 5.1,
        };
        state.measurements.push(created);
        return json(measurementOut(created), 201);
      }
      if (match && method === "GET") {
        return json(state.measurements.filter((m) => m.observation_id === match?.[1]).map(measurementOut));
      }
      match = /^\/api\/lesions\/([^/]+)\/measurements$/.exec(path);
      if (match && method === "GET") {
        return json(
          [...state.measurements]
            .sort((x, y) => (x.captured_at ?? "").localeCompare(y.captured_at ?? ""))
            .map(measurementOut),
        );
      }
      const reportOut = (r: MockState["reports"][number]) => ({
        id: r.id,
        person_id: PERSON_ID,
        scope: r.scope,
        lesion_ids: r.lesion_ids,
        language: r.language,
        paper: r.paper,
        status: r.status,
        bytes: r.status === "ready" ? 32_000 : null,
        pages: r.status === "ready" ? 2 : null,
        error: r.status === "failed" ? "The report could not be made." : null,
        created_at: "2026-10-01T10:00:00Z",
        finished_at: r.status === "ready" ? "2026-10-01T10:00:03Z" : null,
        download_url: r.status === "ready" ? `/api/reports/${r.id}/download` : null,
        can_delete: true,
      });
      match = /^\/api\/persons\/([^/]+)\/reports$/.exec(path);
      if (match && method === "GET") {
        const listed = state.reports.map(reportOut);
        for (const r of state.reports) if (r.status === "queued") r.status = r.fail ? "failed" : "ready";
        return json(listed);
      }
      if (match && method === "POST") {
        const input = body as { scope: string; lesion_id?: string; language?: string; paper?: string };
        const created = {
          id: nextId(),
          scope: input.scope,
          lesion_ids: input.lesion_id ? [input.lesion_id] : [],
          language: input.language ?? "en",
          paper: input.paper ?? "a4",
          status: "queued",
        };
        state.reports.unshift(created);
        return json(reportOut(created), 202);
      }
      match = /^\/api\/reports\/([^/]+)$/.exec(path);
      if (match && method === "DELETE") {
        state.reports = state.reports.filter((r) => r.id !== match?.[1]);
        return new Response(null, { status: 204 });
      }
      const appointmentOut = (a: MockState["appointments"][number]) => ({
        ...a,
        person_name: state.persons.find((p) => p.id === a.person_id)?.display_name ?? "",
        can_edit: true,
        checklist: state.lesions
          .filter((l) => l.person_id === a.person_id)
          .map((l) => {
            const visits = state.observations.filter((o) => o.lesion_id === l.id).map((o) => o.captured_at);
            const last = visits.sort().at(-1) ?? null;
            const state_ =
              last === null ? "never_photographed" : last >= a.created_at ? "photographed" : "to_photograph";
            return {
              lesion_id: l.id,
              label: l.label,
              zone: l.zone,
              state: state_,
              last_observed_at: last,
              next_due_on: last === null ? null : "2026-10-10",
            };
          }),
      });
      if (path === "/api/appointments/upcoming") {
        return json(state.appointments.filter((a) => a.date >= "2026-10-01").map(appointmentOut));
      }
      match = /^\/api\/persons\/([^/]+)\/appointments$/.exec(path);
      if (match && method === "GET") {
        return json(state.appointments.filter((a) => a.person_id === match?.[1]).map(appointmentOut));
      }
      if (match && method === "POST") {
        const input = body as { date: string; notes: string | null };
        const created = {
          id: nextId(),
          person_id: match[1] ?? "",
          date: input.date,
          notes: input.notes,
          report_id: null,
          created_at: "2026-10-01T10:00:00Z",
        };
        state.appointments.push(created);
        return json(appointmentOut(created), 201);
      }
      match = /^\/api\/appointments\/([^/]+)\/report$/.exec(path);
      if (match && method === "POST") {
        const found = state.appointments.find((a) => a.id === match?.[1]);
        if (!found) return json({ detail: "No such appointment." }, 404);
        const input = body as { language?: string; paper?: string };
        const created = {
          id: nextId(),
          scope: "visit",
          lesion_ids: [],
          language: input.language ?? "en",
          paper: input.paper ?? "a4",
          status: "queued",
        };
        state.reports.unshift(created);
        found.report_id = created.id;
        return json(reportOut(created), 202);
      }
      match = /^\/api\/appointments\/([^/]+)$/.exec(path);
      if (match) {
        const found = state.appointments.find((a) => a.id === match?.[1]);
        if (!found) return json({ detail: "No such appointment." }, 404);
        if (method === "DELETE") {
          state.appointments = state.appointments.filter((a) => a.id !== found.id);
          return new Response(null, { status: 204 });
        }
        if (method === "PATCH") {
          const patch = body as { date?: string; notes?: string | null };
          if (patch.date) found.date = patch.date;
          if (patch.notes !== undefined) found.notes = patch.notes;
        }
        return json(appointmentOut(found));
      }
      if (path === "/api/comparisons" && method === "POST") {
        const pair = body as { image_a: string; image_b: string };
        const aligned = state.comparison.status === "aligned";
        const side = (id: string) => ({
          image_id: id,
          upright_width: 640,
          upright_height: 480,
          mm_per_px: 0.05,
          scale_kind: "card",
        });
        return json({
          id: "c1",
          status: state.comparison.status,
          reason: state.comparison.status === "abstained" ? state.comparison.reason : null,
          method: aligned ? "card" : "features",
          inliers: aligned ? null : 6,
          inlier_ratio: aligned ? null : 0.1,
          matrix: aligned
            ? [
                [1, 0, 0],
                [0, 1, 0],
                [0, 0, 1],
              ]
            : null,
          a: side(pair.image_a),
          b: side(pair.image_b),
          overlay_url: aligned ? "/api/comparisons/c1/overlay" : null,
          heatmap_url: aligned ? "/api/comparisons/c1/heatmap" : null,
          coverage: aligned ? 0.98 : null,
          mean_difference: aligned ? 3.1 : null,
        });
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
