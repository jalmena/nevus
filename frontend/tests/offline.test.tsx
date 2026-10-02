import "fake-indexeddb/auto";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { uuid7 } from "@/lib/ids";
import { clearOutbox, queueVisit, queuedVisits, syncOutbox } from "@/lib/offline/outbox";

const USER = "0199a000-0000-7000-8000-000000000001";

describe("client identifiers", () => {
  it("are UUIDv7: version 7, variant 10, ordered by time", () => {
    const a = uuid7(1_700_000_000_000);
    const b = uuid7(1_700_000_000_001);
    expect(a).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(a < b).toBe(true);
  });
});

describe("the offline queue", () => {
  const calls: { url: string; body: unknown }[] = [];

  beforeEach(async () => {
    calls.length = 0;
    await clearOutbox();
  });
  afterEach(() => vi.unstubAllGlobals());

  function stubServer(failPhotosOnce = false) {
    let photoFailures = failPhotosOnce ? 1 : 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        calls.push({
          url,
          body: init?.body instanceof FormData ? Object.fromEntries(init.body.entries()) : init?.body,
        });
        if (url.endsWith("/images") && photoFailures > 0) {
          photoFailures -= 1;
          return new Response("{}", { status: 503 });
        }
        return new Response("{}", { status: 201, headers: { "content-type": "application/json" } });
      }),
    );
  }

  it("keeps a visit with its photos and uploads it once, with the identifiers minted on the device", async () => {
    stubServer();
    const id = await queueVisit({
      userId: USER,
      lesionId: "l1",
      lesionLabel: "Chest",
      notes: "taken offline",
      photos: [{ file: new Blob(["jpeg"], { type: "image/jpeg" }), role: "close_up", name: "a.jpg" }],
    });
    expect((await queuedVisits(USER)).map((v) => v.id)).toEqual([id]);
    expect(await syncOutbox(USER)).toBe(1);
    expect(await queuedVisits(USER)).toEqual([]);
    const visitCall = calls.find((c) => c.url.endsWith("/api/lesions/l1/observations"));
    expect(JSON.parse(String(visitCall?.body))).toMatchObject({ id, notes: "taken offline" });
    const photoCall = calls.find((c) => c.url.endsWith(`/api/observations/${id}/images`));
    expect(photoCall?.body).toMatchObject({ role: "close_up" });
  });

  it("keeps what failed and finishes on the next run without sending the visit as a new one", async () => {
    stubServer(true);
    const id = await queueVisit({
      userId: USER,
      lesionId: "l1",
      lesionLabel: "Chest",
      notes: null,
      photos: [{ file: new Blob(["jpeg"]), role: "close_up", name: "a.jpg" }],
    });
    expect(await syncOutbox(USER)).toBe(0);
    const [failed] = await queuedVisits(USER);
    expect(failed?.status).toBe("failed");
    expect(await syncOutbox(USER)).toBe(1);
    const visitCalls = calls.filter((c) => c.url.endsWith("/observations"));
    expect(visitCalls.map((c) => JSON.parse(String(c.body)).id)).toEqual([id, id]);
  });

  it("belongs to one account and is emptied on sign-out", async () => {
    await queueVisit({ userId: USER, lesionId: "l1", lesionLabel: "Chest", notes: "x", photos: [] });
    expect(await queuedVisits("someone-else")).toEqual([]);
    await clearOutbox();
    expect(await queuedVisits(USER)).toEqual([]);
  });
});
