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

export interface MockSessionMark {
  id: string;
  x: number;
  y: number;
  lesion_id: string | null;
  source: "person" | "candidate";
  state: "pending" | "confirmed" | "rejected";
  match: "matched" | "new" | "uncertain" | null;
}

export interface MockBodySession {
  id: string;
  person_id: string;
  status: "open" | "finished";
  started_at: string;
  zones: Record<
    string,
    { status: "pending" | "captured" | "skipped"; image_id: string | null; marks: MockSessionMark[] }
  >;
}

/** The capture protocol, as the server describes it. */
export const PROTOCOL = [
  { id: "face", covers: ["1100", "3150", "3151", "3171"], sensitive: false },
  { id: "scalp", covers: ["2100", "3170", "3172"], sensitive: false },
  { id: "chest", covers: ["1200", "1250", "1251", "1650", "1651"], sensitive: false },
  { id: "abdomen", covers: ["1300", "1301", "1350", "1351"], sensitive: true },
  { id: "upper-back", covers: ["2200", "2250", "2251", "2650", "2651"], sensitive: false },
  { id: "lower-back", covers: ["2300", "2301", "2350", "2351"], sensitive: true },
  { id: "right-arm-front", covers: ["1700", "1750", "1800"], sensitive: false },
  { id: "left-arm-front", covers: ["1701", "1751", "1801"], sensitive: false },
  { id: "right-arm-back", covers: ["2701", "2751", "2801"], sensitive: false },
  { id: "left-arm-back", covers: ["2700", "2750", "2800"], sensitive: false },
  { id: "palms", covers: ["1850", "1851", "3210", "3211"], sensitive: false },
  { id: "backs-of-hands", covers: ["2850", "2851", "3220", "3221"], sensitive: false },
  { id: "right-leg-front", covers: ["1400", "1450", "1500", "1550"], sensitive: false },
  { id: "left-leg-front", covers: ["1401", "1451", "1501", "1551"], sensitive: false },
  { id: "right-leg-back", covers: ["2401", "2451", "2501", "2551"], sensitive: false },
  { id: "left-leg-back", covers: ["2400", "2450", "2500", "2550"], sensitive: false },
  { id: "tops-of-feet", covers: ["1600", "1601", "3320", "3321"], sensitive: false },
  { id: "soles", covers: ["2600", "2601", "3310", "3311"], sensitive: false },
];

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
  webhooks: { id: string; name: string; preset: string; url: string; enabled: boolean }[];
  /** Experimental outline proposals by image id. */
  proposals: Record<
    string,
    { id: string; found: boolean; reason?: string; decision: string; framing?: string[] }[]
  >;
  /** Labels of the personal evaluation set, by image id. */
  labels: Record<string, { outline: number[][] | null; quality: string | null }>;
  /** "proxy": a reverse proxy signs people in; there are no local passwords. */
  authMode: "local" | "proxy";
  /** Whether the experimental analysis is on for every person. */
  experimental: boolean;
  /** The signed-in account's second factor. The mock accepts the code 123456 and the recovery code aaaaa-bbbbb. */
  totp: { enabled: boolean; settingUp: boolean; codesLeft: number; pending: boolean };
  /** The backups' state, as the administrator sees it. */
  backups: {
    enabled: boolean;
    backup_hour: number;
    verify_days: number;
    count: number;
    latest: { file: string; bytes: number; created_at: string } | null;
    verification: {
      ok: boolean;
      checked_at: string;
      archive: string | null;
      blobs_in_archive: number | null;
      problems: string[];
    } | null;
    backup_queued: boolean;
    verification_queued: boolean;
  };
  /** Push notifications: the server's flag and this user's subscribed devices. */
  push: { enabled: boolean; public_key: string | null; subscriptions: number };
  /** Accounts, for the administrator's list. */
  users: {
    id: string;
    username: string;
    role: string;
    disabled_at: string | null;
    totp_enabled: boolean;
    last_login_at: string | null;
  }[];
  /** Full-body sessions; with the experimental analysis on, a zone photo gets one proposed spot. */
  bodySessions: MockBodySession[];
  calendar: { exists: boolean };
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
    webhooks: [],
    calendar: { exists: false },
    authMode: "local",
    proposals: {},
    labels: {},
    experimental: false,
    bodySessions: [],
    totp: { enabled: false, settingUp: false, codesLeft: 0, pending: false },
    push: { enabled: false, public_key: null, subscriptions: 0 },
    users: [],
    backups: {
      enabled: true,
      backup_hour: 3,
      verify_days: 7,
      count: 3,
      latest: {
        file: "nevus-backup-20261002T030000Z.tar.age",
        bytes: 52_000_000,
        created_at: "2026-10-02T03:00:00Z",
      },
      verification: {
        ok: true,
        checked_at: "2026-10-02T04:00:00Z",
        archive: "nevus-backup-20261002T030000Z.tar.age",
        blobs_in_archive: 412,
        problems: [],
      },
      backup_queued: false,
      verification_queued: false,
    },
    ...initial,
  };
  const personOut = (p: { id: string; display_name: string }) => ({
    ...p,
    birth_year: null,
    skin_tone: null,
    owner_user_id: "0199a000-0000-7000-8000-000000000001",
    experimental_analysis: state.experimental,
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
    descriptors: {
      version: "1.0.0",
      shape: { perimeter_mm: 15.7, compactness: 0.93, aspect: 0.96 },
      colour: {
        reference: "card_grey",
        mark: { L: 35.2, a: 12.1, b: 18.4, hex: "#6b4a3a" },
        skin: { L: 68.5, a: 14.0, b: 22.3, hex: "#c89a7e" },
        contrast: 33.4,
        lightness_spread: 4.2,
        pixels: 1200,
      },
    },
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
      if (path === "/api/auth/instance") {
        return json({
          claimed: state.claimed,
          version: "test",
          auth_mode: state.authMode,
          logout_url: state.authMode === "proxy" ? "https://sso.example/out" : null,
        });
      }
      if (path === "/api/auth/session") {
        return state.session
          ? json({
              user: {
                ...user(
                  state.session.username,
                  state.session.language,
                  state.session.theme,
                  state.session.role ?? "admin",
                  state.session.email ?? null,
                  state.session.showUncertainty ?? true,
                ),
                totp_enabled: state.totp.enabled,
              },
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
        if (state.totp.enabled) {
          state.totp.pending = true;
          return json({ session: null, second_factor_required: true });
        }
        state.session = { username: creds.username.toLowerCase(), language: "en", theme: "system" };
        return json({
          session: { user: user(state.session.username), sudo_until: null },
          second_factor_required: false,
        });
      }
      if (path === "/api/auth/second-factor" && method === "POST") {
        const input = body as { code?: string | null; recovery_code?: string | null };
        if (!state.totp.pending) return json({ detail: "Sign in with your password first." }, 401);
        const recovery = (input.recovery_code ?? "").replace(/[\s-]/g, "").toLowerCase();
        if (input.code !== "123456" && recovery !== "aaaaabbbbb") return json({ detail: "Wrong code." }, 401);
        if (recovery) state.totp.codesLeft = Math.max(0, state.totp.codesLeft - 1);
        state.totp.pending = false;
        state.session = { username: "jose", language: "en", theme: "system" };
        return json({ user: { ...user("jose"), totp_enabled: true }, sudo_until: null });
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
        if (method === "DELETE") {
          state.lesions = state.lesions.filter((l) => l.id !== found.id);
          state.observations = state.observations.filter((o) => o.lesion_id !== found.id);
          return new Response(null, { status: 204 });
        }
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
        const given = body as { password?: string };
        if (state.authMode !== "proxy" && given.password !== "correct horse battery")
          return json({ detail: "Wrong password." }, 401);
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
      if (path === "/api/push" && method === "GET") return json(state.push);
      if (path === "/api/push/subscriptions" && method === "POST") {
        if (!state.push.enabled) return json({ detail: "Push notifications are off on this server." }, 404);
        state.push.subscriptions += 1;
        return json(state.push, 201);
      }
      if (path === "/api/push/subscriptions" && method === "DELETE") {
        state.push.subscriptions = Math.max(0, state.push.subscriptions - 1);
        return new Response(null, { status: 204 });
      }
      if (path === "/api/push/test" && method === "POST")
        return json({ sent: state.push.subscriptions, failed: 0 });
      if (path === "/api/admin/backups" && method === "GET") return json(state.backups);
      if (path === "/api/admin/backups/run" && method === "POST") {
        if (!state.backups.enabled) return json({ detail: "Set NEVUS_BACKUP_PASSPHRASE first." }, 409);
        state.backups.backup_queued = true;
        return json({ queued: true }, 202);
      }
      if (path === "/api/admin/backups/verify" && method === "POST") {
        if (!state.backups.enabled) return json({ detail: "Set NEVUS_BACKUP_PASSPHRASE first." }, 409);
        state.backups.verification_queued = true;
        return json({ queued: true }, 202);
      }
      if (path.startsWith("/api/evaluation/photos") && method === "GET") {
        const only = new URL(url).searchParams.get("only") ?? "all";
        const all = state.observations.flatMap((o) => o.images);
        return json(
          all
            .filter((id) =>
              only === "unlabelled" ? !state.labels[id] : only === "labelled" ? !!state.labels[id] : true,
            )
            .map((id) => ({
              image_id: id,
              person_name: "Ana",
              skin_tone: "MST3",
              mark: "Chest mark",
              zone: "1250",
              captured_on: "2026-09-01",
              role: "close_up",
              upright_width: 640,
              upright_height: 480,
              quality_flags: [],
              proposal: [
                [300, 220],
                [340, 220],
                [340, 260],
                [300, 260],
              ],
              label: state.labels[id] ? { ...state.labels[id], labelled_at: "2026-10-01T10:00:00Z" } : null,
            })),
        );
      }
      if (path === "/api/evaluation/summary") {
        const n = Object.keys(state.labels).length;
        const row = {
          photos: n,
          found: n,
          mean_iou: n ? 0.92 : null,
          mean_dice: n ? 0.96 : null,
          mean_diameter_error: n ? 0.03 : null,
          worst_diameter_error: n ? 0.05 : null,
        };
        return json({
          analyzer: { name: "segment.auto", version: "1.0.0" },
          labelled: n,
          outline: { overall: row, by_tone: n ? { MST3: row } : {} },
          quality: {
            overall: {
              photos: 0,
              agreement: null,
              poor_caught: 0,
              poor_missed: 0,
              good_flagged: 0,
              good_clear: 0,
            },
            by_tone: {},
          },
        });
      }
      match = /^\/api\/evaluation\/photos\/([^/]+)\/label$/.exec(path);
      if (match && method === "PUT") {
        const input = body as { outline: number[][] | null; quality: string | null };
        state.labels[match[1] ?? ""] = input;
        return json({ ...input, labelled_at: "2026-10-01T10:00:00Z" });
      }
      match = /^\/api\/images\/([^/]+)\/proposals$/.exec(path);
      if (match && method === "GET") {
        return json(
          (state.proposals[match[1] ?? ""] ?? []).map((item) => ({
            id: item.id,
            image_id: match?.[1],
            analyzer: "segment.auto",
            version: "1.0.0",
            found: item.found,
            reason: item.found ? null : (item.reason ?? "no_mark_found"),
            outline: item.found
              ? [
                  [300, 220],
                  [340, 220],
                  [340, 260],
                  [300, 260],
                ]
              : null,
            confidence: item.found ? 0.9 : null,
            framing_flags: item.framing ?? [],
            decision: item.decision,
            created_at: "2026-10-01T10:00:00Z",
            size: item.found
              ? {
                  scale_reference_id: "ref-card",
                  scale_kind: "card",
                  longest_mm: 5.1,
                  perpendicular_mm: 4.9,
                  area_mm2: 19.6,
                  sigma_longest_mm: 0.2,
                  sigma_perpendicular_mm: 0.2,
                  sigma_area_mm2: 1.5,
                }
              : null,
          })),
        );
      }
      match = /^\/api\/proposals\/([^/]+)\/(confirm|reject)$/.exec(path);
      if (match && method === "POST") {
        const all = Object.values(state.proposals).flat();
        const found = all.find((item) => item.id === match?.[1]);
        if (!found) return json({ detail: "No such proposal." }, 404);
        found.decision = match[2] === "confirm" ? "confirmed" : "rejected";
        if (match[2] === "confirm") {
          const created = { id: nextId(), observation_id: "o1", image_id: "i1", longest_mm: 5.1 };
          state.measurements.push(created);
          return json(measurementOut(created), 201);
        }
        return json({ id: found.id, decision: found.decision });
      }
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
        const input = body as {
          scope: string;
          lesion_id?: string;
          lesion_ids?: string[];
          language?: string;
          paper?: string;
        };
        const created = {
          id: nextId(),
          scope: input.scope,
          lesion_ids: input.lesion_ids ?? (input.lesion_id ? [input.lesion_id] : []),
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
      const hookOut = (h: MockState["webhooks"][number]) => ({
        id: h.id,
        name: h.name,
        preset: h.preset,
        url_hint: h.url.slice(0, 30),
        has_secret: false,
        enabled: h.enabled,
        last_status: null,
        last_error: null,
        last_sent_at: null,
        created_at: "2026-10-01T10:00:00Z",
      });
      if (path === "/api/admin/webhooks" && method === "GET") return json(state.webhooks.map(hookOut));
      if (path === "/api/admin/webhooks" && method === "POST") {
        const input = body as { name: string; preset: string; url: string; enabled: boolean };
        const created = {
          id: nextId(),
          name: input.name,
          preset: input.preset,
          url: input.url,
          enabled: input.enabled,
        };
        state.webhooks.push(created);
        return json(hookOut(created), 201);
      }
      match = /^\/api\/admin\/webhooks\/([^/]+)\/test$/.exec(path);
      if (match && method === "POST") return json({ ok: true, detail: null });
      match = /^\/api\/admin\/webhooks\/([^/]+)$/.exec(path);
      if (match) {
        const found = state.webhooks.find((h) => h.id === match?.[1]);
        if (!found) return json({ detail: "No such webhook." }, 404);
        if (method === "DELETE") {
          state.webhooks = state.webhooks.filter((h) => h.id !== found.id);
          return new Response(null, { status: 204 });
        }
        const patch = body as { enabled?: boolean };
        if (patch.enabled !== undefined) found.enabled = patch.enabled;
        return json(hookOut(found));
      }
      match = /^\/api\/persons\/([^/]+)\/calendar$/.exec(path);
      if (match) {
        if (method === "POST") {
          state.calendar.exists = true;
          return json(
            { url: "http://localhost/api/calendar/secret-token-123.ics", created_at: "2026-10-01T10:00:00Z" },
            201,
          );
        }
        if (method === "DELETE") {
          state.calendar.exists = false;
          return new Response(null, { status: 204 });
        }
        return json({
          exists: state.calendar.exists,
          created_at: state.calendar.exists ? "2026-10-01T10:00:00Z" : null,
          last_used_at: null,
        });
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
      if (path === "/api/sessions/protocol") return json(PROTOCOL);
      const markOut = (m: MockSessionMark) => ({ ...m, crop_url: `/api/session-marks/${m.id}/crop` });
      const sessionOut = (row: MockBodySession) => ({
        id: row.id,
        person_id: row.person_id,
        protocol: "nevus-session-protocol/1",
        status: row.status,
        notes: null,
        started_at: row.started_at,
        finished_at: row.status === "finished" ? row.started_at : null,
        zones: PROTOCOL.map((capture) => {
          const zone = row.zones[capture.id] ?? { status: "pending", image_id: null, marks: [] };
          return {
            zone: capture.id,
            status: zone.status,
            image_id: zone.image_id,
            upright_width: zone.image_id ? 640 : null,
            upright_height: zone.image_id ? 480 : null,
            marks: zone.marks
              .filter((m) => m.state !== "rejected" && (m.source === "person" || state.experimental))
              .map(markOut),
            analysing: false,
          };
        }),
        can_edit: true,
        experimental: state.experimental,
      });
      const findMark = (id: string) => {
        for (const row of state.bodySessions)
          for (const zone of Object.values(row.zones)) {
            const mark = zone.marks.find((m) => m.id === id);
            if (mark) return { row, zone, mark };
          }
        return null;
      };
      const linkTo = (
        input: { lesion_id?: string | null; new_mark?: { zone_code: string; label: string | null } | null },
        personId: string,
      ) => {
        if (input.lesion_id) return input.lesion_id;
        if (!input.new_mark) return null;
        const id = nextId();
        state.lesions.push({
          id,
          person_id: personId,
          label: input.new_mark.label,
          zone: input.new_mark.zone_code,
          x: 0.5,
          y: 0.3,
          due: false,
        });
        return id;
      };
      match = /^\/api\/persons\/([^/]+)\/sessions$/.exec(path);
      if (match && method === "POST") {
        const row: MockBodySession = {
          id: nextId(),
          person_id: match[1] ?? "",
          status: "open",
          started_at: "2026-10-01T10:00:00Z",
          zones: {},
        };
        state.bodySessions.unshift(row);
        return json(sessionOut(row), 201);
      }
      if (match && method === "GET") {
        return json(
          state.bodySessions
            .filter((row) => row.person_id === match?.[1])
            .map((row) => {
              const zones = PROTOCOL.map((capture) => row.zones[capture.id]?.status ?? "pending");
              return {
                id: row.id,
                status: row.status,
                started_at: row.started_at,
                finished_at: null,
                captured: zones.filter((z) => z === "captured").length,
                skipped: zones.filter((z) => z === "skipped").length,
                pending: zones.filter((z) => z === "pending").length,
                marks: Object.values(row.zones).flatMap((z) => z.marks.filter((m) => m.state === "confirmed"))
                  .length,
              };
            }),
        );
      }
      match = /^\/api\/sessions\/([^/]+)\/compare\/([^/]+)$/.exec(path);
      if (match) {
        const [one, two] = [match[1], match[2]].map((id) => state.bodySessions.find((row) => row.id === id));
        if (!one || !two) return json({ detail: "No such session." }, 404);
        const [earlier, later] = [one, two].sort((a, b) => a.started_at.localeCompare(b.started_at));
        return json(
          PROTOCOL.filter((c) => earlier?.zones[c.id]?.image_id && later?.zones[c.id]?.image_id).map((c) => ({
            zone: c.id,
            earlier_image_id: earlier?.zones[c.id]?.image_id,
            later_image_id: later?.zones[c.id]?.image_id,
          })),
        );
      }
      match = /^\/api\/sessions\/([^/]+)(?:\/(finish)|\/zones\/([^/]+)\/(photo|skip|marks|blur))?$/.exec(
        path,
      );
      if (match) {
        const row = state.bodySessions.find((item) => item.id === match?.[1]);
        if (!row) return json({ detail: "No such session." }, 404);
        const [, , finish, zoneId, action] = match;
        if (!finish && !action) {
          if (method === "DELETE") {
            state.bodySessions = state.bodySessions.filter((item) => item !== row);
            return new Response(null, { status: 204 });
          }
          return json(sessionOut(row));
        }
        if (finish) {
          row.status = "finished";
          return json(sessionOut(row));
        }
        const zone = (row.zones[zoneId ?? ""] ??= { status: "pending", image_id: null, marks: [] });
        if (action === "blur") {
          if (!zone.image_id) return json({ detail: "Take the zone's photo first." }, 409);
          zone.image_id = nextId();
          return json(sessionOut(row));
        }
        if (action === "photo") {
          const file = form?.get("file");
          if (!(file instanceof File) || file.size === 0)
            return json({ detail: "The upload is empty." }, 400);
          zone.status = "captured";
          zone.image_id = nextId();
          zone.marks = state.experimental
            ? [
                {
                  id: nextId(),
                  x: 0.4,
                  y: 0.5,
                  lesion_id: null,
                  source: "candidate",
                  state: "pending",
                  match: "new",
                },
              ]
            : [];
          return json(sessionOut(row));
        }
        if (action === "skip") {
          if (method === "POST" && zone.status === "captured")
            return json({ detail: "This zone already has a photo." }, 409);
          zone.status = method === "POST" ? "skipped" : zone.status === "skipped" ? "pending" : zone.status;
          return json(sessionOut(row));
        }
        const input = body as {
          x: number;
          y: number;
          lesion_id?: string | null;
          new_mark?: { zone_code: string; label: string | null } | null;
        };
        const mark: MockSessionMark = {
          id: nextId(),
          x: input.x,
          y: input.y,
          lesion_id: linkTo(input, row.person_id),
          source: "person",
          state: "confirmed",
          match: null,
        };
        zone.marks.push(mark);
        return json(markOut(mark), 201);
      }
      match = /^\/api\/session-marks\/([^/]+)$/.exec(path);
      if (match) {
        const found = findMark(match[1] ?? "");
        if (!found) return json({ detail: "No such mark." }, 404);
        if (method === "DELETE") {
          found.zone.marks = found.zone.marks.filter((m) => m !== found.mark);
          return new Response(null, { status: 204 });
        }
        const input = body as {
          state?: "confirmed" | "rejected" | null;
          lesion_id?: string | null;
          new_mark?: { zone_code: string; label: string | null } | null;
        };
        const linked = linkTo(input, found.row.person_id);
        if (linked) found.mark.lesion_id = linked;
        found.mark.state = input.state ?? (linked ? "confirmed" : found.mark.state);
        return json(markOut(found.mark));
      }
      match = /^\/api\/lesions\/([^/]+)\/sightings$/.exec(path);
      if (match) {
        return json(
          state.bodySessions.flatMap((row) =>
            Object.entries(row.zones).flatMap(([zone, item]) =>
              item.marks
                .filter((m) => m.lesion_id === match?.[1] && m.state === "confirmed")
                .map((m) => ({
                  mark_id: m.id,
                  session_id: row.id,
                  zone,
                  started_at: row.started_at,
                  crop_url: `/api/session-marks/${m.id}/crop`,
                })),
            ),
          ),
        );
      }
      const RECOVERY = [
        "aaaaa-bbbbb",
        "ccccc-ddddd",
        "eeeee-fffff",
        "ggggg-hhhhh",
        "jjjjj-kkkkk",
        "mmmmm-nnnnn",
        "ppppp-qqqqq",
        "rrrrr-sssss",
        "ttttt-uuuuu",
        "vvvvv-wwwww",
      ];
      if (path === "/api/auth/totp" && method === "GET") {
        return json({
          enabled: state.totp.enabled,
          enabled_at: state.totp.enabled ? "2026-10-01T10:00:00Z" : null,
          setting_up: state.totp.settingUp,
          recovery_codes_left: state.totp.codesLeft,
        });
      }
      if (path === "/api/auth/totp" && method === "DELETE") {
        if (!state.sudo) return needSudo();
        state.totp = { enabled: false, settingUp: false, codesLeft: 0, pending: false };
        return new Response(null, { status: 204 });
      }
      if (path === "/api/auth/totp/setup" && method === "POST") {
        if (!state.sudo) return needSudo();
        state.totp.settingUp = true;
        return json({
          secret: "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP",
          otpauth_uri: "otpauth://totp/neVus:jose?secret=JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP&issuer=neVus",
          qr_svg: "<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'></svg>",
        });
      }
      if (path === "/api/auth/totp/enable" && method === "POST") {
        if (!state.sudo) return needSudo();
        if ((body as { code: string }).code !== "123456")
          return json(
            { detail: "That code does not match. Check the time on the phone and try the next one." },
            400,
          );
        state.totp = { enabled: true, settingUp: false, codesLeft: 10, pending: false };
        return json({ recovery_codes: RECOVERY });
      }
      if (path === "/api/auth/totp/recovery-codes" && method === "POST") {
        if (!state.sudo) return needSudo();
        state.totp.codesLeft = 10;
        return json({ recovery_codes: RECOVERY });
      }
      const userOut = (account: MockState["users"][number]) => ({
        ...user(account.username, "en", "system", account.role),
        id: account.id,
        disabled_at: account.disabled_at,
        totp_enabled: account.totp_enabled,
        last_login_at: account.last_login_at,
      });
      if (path === "/api/users" && method === "GET") return json(state.users.map(userOut));
      if (path === "/api/users" && method === "POST") {
        const input = body as { username: string; password: string; role: string };
        if (state.users.some((account) => account.username === input.username.toLowerCase()))
          return json({ detail: "That username is taken." }, 409);
        const created = {
          id: nextId(),
          username: input.username.toLowerCase(),
          role: input.role,
          disabled_at: null,
          totp_enabled: false,
          last_login_at: null,
        };
        state.users.push(created);
        return json(userOut(created), 201);
      }
      match = /^\/api\/users\/([^/]+)\/(enable|disable|password|totp)$/.exec(path);
      if (match) {
        const account = state.users.find((item) => item.id === match?.[1]);
        if (!account) return json({ detail: "No such user." }, 404);
        if (match[2] === "totp") {
          if (!state.sudo) return needSudo();
          account.totp_enabled = false;
          return new Response(null, { status: 204 });
        }
        if (match[2] === "password") return new Response(null, { status: 204 });
        account.disabled_at = match[2] === "disable" ? "2026-10-02T10:00:00Z" : null;
        return json(userOut(account));
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
