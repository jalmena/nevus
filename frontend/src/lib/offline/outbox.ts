import Dexie, { type Table } from "dexie";
import { uuid7 } from "@/lib/ids";

/**
 * Visits recorded without a connection wait here, on this device, until they can be uploaded.
 * Identifiers are minted here, so sending a visit twice (a lost reply, a retry) changes nothing.
 * The queue belongs to the account that filled it and is emptied on sign-out.
 */
export interface QueuedVisit {
  id: string;
  userId: string;
  lesionId: string;
  lesionLabel: string;
  capturedAt: string;
  capturedTz: string;
  notes: string | null;
  status: "pending" | "uploading" | "failed";
  error: string | null;
  createdAt: number;
}

export interface QueuedPhoto {
  id: string;
  visitId: string;
  role: string;
  name: string;
  /** Bytes rather than a Blob: every IndexedDB implementation stores an ArrayBuffer faithfully. */
  data: ArrayBuffer;
  type: string;
}

class OutboxDb extends Dexie {
  visits!: Table<QueuedVisit, string>;
  photos!: Table<QueuedPhoto, string>;

  constructor() {
    super("nevus-outbox");
    this.version(1).stores({ visits: "id, userId, status, createdAt", photos: "id, visitId" });
  }
}

export const outbox = new OutboxDb();
const CHANGED = "nevus:outbox-changed";

export function onOutboxChange(listener: () => void): () => void {
  window.addEventListener(CHANGED, listener);
  return () => window.removeEventListener(CHANGED, listener);
}

function changed() {
  window.dispatchEvent(new Event(CHANGED));
}

export async function queueVisit(input: {
  userId: string;
  lesionId: string;
  lesionLabel: string;
  notes: string | null;
  photos: { file: Blob; role: string; name: string }[];
}): Promise<string> {
  const id = uuid7();
  const prepared = await Promise.all(
    input.photos.map(async (photo) => ({
      id: uuid7(),
      visitId: id,
      role: photo.role,
      name: photo.name,
      data: await readBytes(photo.file),
      type: photo.file.type || "image/jpeg",
    })),
  );
  await outbox.transaction("rw", outbox.visits, outbox.photos, async () => {
    await outbox.visits.add({
      id,
      userId: input.userId,
      lesionId: input.lesionId,
      lesionLabel: input.lesionLabel,
      capturedAt: new Date().toISOString(),
      capturedTz: Intl.DateTimeFormat().resolvedOptions().timeZone,
      notes: input.notes,
      status: "pending",
      error: null,
      createdAt: Date.now(),
    });
    for (const photo of prepared) await outbox.photos.add(photo);
  });
  changed();
  return id;
}

export async function queuedVisits(userId: string): Promise<QueuedVisit[]> {
  return outbox.visits.where("userId").equals(userId).sortBy("createdAt");
}

async function upload(visit: QueuedVisit): Promise<void> {
  const origin = window.location.origin;
  const response = await fetch(`${origin}/api/lesions/${visit.lesionId}/observations`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      id: visit.id,
      captured_at: visit.capturedAt,
      captured_tz: visit.capturedTz,
      notes: visit.notes,
    }),
  });
  if (!response.ok) throw new Error(`visit ${response.status}`);
  const photos = await outbox.photos.where("visitId").equals(visit.id).toArray();
  for (const photo of photos) {
    const body = new FormData();
    body.append("file", new Blob([photo.data], { type: photo.type }), photo.name);
    body.append("role", photo.role);
    body.append("client_id", photo.id);
    body.append("captured_tz", visit.capturedTz);
    const sent = await fetch(`${origin}/api/observations/${visit.id}/images`, {
      method: "POST",
      credentials: "same-origin",
      body,
    });
    if (!sent.ok) throw new Error(`photo ${sent.status}`);
    await outbox.photos.delete(photo.id);
  }
}

/** Blob.arrayBuffer, or FileReader where a test environment's Blob lacks it. */
function readBytes(blob: Blob): Promise<ArrayBuffer> {
  if (typeof blob.arrayBuffer === "function") return blob.arrayBuffer();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = () => reject(reader.error ?? new Error("unreadable photo"));
    reader.readAsArrayBuffer(blob);
  });
}

let running: Promise<number> | null = null;

/** Upload everything waiting for this account. Safe to call often: one run at a time, retries are no-ops. */
export function syncOutbox(userId: string): Promise<number> {
  if (running) return running;
  running = (async () => {
    let done = 0;
    for (const visit of await queuedVisits(userId)) {
      await outbox.visits.update(visit.id, { status: "uploading", error: null });
      changed();
      try {
        await upload(visit);
        await outbox.visits.delete(visit.id);
        done += 1;
      } catch (error) {
        await outbox.visits.update(visit.id, { status: "failed", error: (error as Error).message });
      }
      changed();
    }
    return done;
  })().finally(() => {
    running = null;
  });
  return running;
}

export async function clearOutbox(): Promise<void> {
  await outbox.transaction("rw", outbox.visits, outbox.photos, async () => {
    await outbox.visits.clear();
    await outbox.photos.clear();
  });
  changed();
}
