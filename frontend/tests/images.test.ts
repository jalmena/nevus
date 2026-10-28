import { describe, expect, it } from "vitest";
import { stillAnalysing, thumbOf } from "@/lib/images";

const rendition = (kind: string) => ({ kind, width: 1, height: 1, bytes: 1 });

describe("thumbOf", () => {
  it("names the mark's thumbnail once the server has cut it, so the picture changes with the record", () => {
    expect(thumbOf({ id: "i1", renditions: [rendition("thumb"), rendition("preview")] })).toBe(
      "/api/images/i1/thumb",
    );
    expect(thumbOf({ id: "i1", renditions: [rendition("thumb"), rendition("normalised_thumb")] })).toBe(
      "/api/images/i1/normalised_thumb",
    );
    expect(
      thumbOf({
        id: "i1",
        renditions: [rendition("thumb"), rendition("normalised_thumb"), rendition("mark_thumb")],
      }),
    ).toBe("/api/images/i1/mark_thumb");
  });
});

describe("stillAnalysing", () => {
  const now = Date.parse("2026-10-28T12:00:00Z");
  const fresh = "2026-10-28T11:59:30Z";
  it("keeps looking while a fresh photo lacks its quality check or its settled analysis", () => {
    expect(stillAnalysing({ quality_checked_at: null, analysed_at: null, created_at: fresh }, now)).toBe(
      true,
    );
    expect(stillAnalysing({ quality_checked_at: fresh, analysed_at: null, created_at: fresh }, now)).toBe(
      true,
    );
    expect(stillAnalysing({ quality_checked_at: fresh, analysed_at: fresh, created_at: fresh }, now)).toBe(
      false,
    );
  });
  it("gives up on a photo whose analysis never settled, so a page does not poll forever", () => {
    const old = "2026-10-28T11:00:00Z";
    expect(stillAnalysing({ quality_checked_at: old, analysed_at: null, created_at: old }, now)).toBe(false);
  });
});
