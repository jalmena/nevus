import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";
import { createHmac } from "node:crypto";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

export const PHOTO = fileURLToPath(new URL("./fixtures/card-disc-5mm.jpg", import.meta.url));
export const PASSWORD = "correct horse battery";

/** Fails on serious or critical WCAG 2.2 AA findings on the current page. */
export async function accessible(page: Page, name: string) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  const where = (v: (typeof blocking)[number]) => v.nodes.map((n) => n.target.join(" ")).join(", ");
  expect(blocking.map((v) => `${name}: ${v.id} at ${where(v)}`)).toEqual([]);
}

/** Signs in as the administrator, claiming the instance when nobody has yet. */
export async function signIn(page: Page) {
  await page.goto("/");
  const claim = page.getByRole("heading", { name: "Claim this instance", exact: true });
  await expect(claim.or(page.getByRole("heading", { name: "Sign in", exact: true }))).toBeVisible();
  await page.getByLabel("Username").fill("Jose");
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  if (await claim.isVisible()) {
    await page.getByLabel("Repeat the password").fill(PASSWORD);
    await page.getByRole("button", { name: "Create the administrator", exact: true }).click();
  } else {
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
  }
  await expect(page.getByRole("heading", { name: "Persons", exact: true })).toBeVisible();
}

/** A visit with a photo of the card, and the 5 mm disc in its window measured. */
export async function measuredVisit(page: Page, first: boolean) {
  await page.getByRole("button", { name: "New visit", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Photos", exact: true })).toBeVisible();
  await page.getByLabel("Kind").selectOption("with_reference");
  await page.getByLabel("Choose a file").setInputFiles(PHOTO);
  await expect(page.getByRole("button", { name: /Open the photo/ })).toBeVisible();
  await expect(page.getByText("Checking the photos…")).toHaveCount(0, { timeout: 60_000 });
  if (first) await accessible(page, "visit");

  await page.getByRole("link", { name: "Measure on the photo", exact: true }).click();
  await expect(page.getByText(/Reference card found/)).toBeVisible({ timeout: 60_000 });
  if (first) await accessible(page, "measure");
  await page.getByRole("button", { name: "Use the reference card", exact: true }).click();

  // Tap the middle of the card's window, where the 5 mm disc is.
  const scale = await page.evaluate(async () => {
    const path = window.location.pathname.split("/");
    const imageId = path[path.length - 1];
    const response = await fetch(`/api/images/${imageId}/scale`);
    return (await response.json()) as {
      upright_width: number;
      upright_height: number;
      card: { centre_px: number[] };
    };
  });
  const canvas = page.getByRole("application");
  const box = await canvas.boundingBox();
  if (!box) throw new Error("no canvas");
  const [cx = 0, cy = 0] = scale.card.centre_px;
  await page.mouse.click(
    box.x + (cx / scale.upright_width) * box.width,
    box.y + (cy / scale.upright_height) * box.height,
  );

  const longest = page.locator("dt", { hasText: "Longest" }).locator("xpath=following-sibling::dd");
  await expect(longest).toHaveText(/^\d+\.\d ± \d+\.\d mm$/, { timeout: 20_000 });
  const value = Number((await longest.textContent())?.split(" ")[0]);
  expect(Math.abs(value - 5.0)).toBeLessThanOrEqual(0.3);
  await page.getByRole("button", { name: "Save the measurement", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Measurements", exact: true })).toBeVisible();
}

/** Screenshots for a human look at layout and both themes, into the directory given (none: no shots). */
export async function shot(page: Page, name: string, dir = process.env.NEVUS_E2E_SHOTS) {
  if (!dir) return;
  mkdirSync(dir, { recursive: true });
  for (const scheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: scheme });
    await page.waitForTimeout(400); // let colour transitions finish
    await page.screenshot({ path: `${dir}/${name}-${scheme}.png`, fullPage: true });
  }
  await page.emulateMedia({ colorScheme: "light" });
}

/** A time-based one-time code (RFC 6238, SHA-1, six digits), as an authenticator app would show it. */
export function totpCode(secret: string, at = Date.now()): string {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const char of secret.toUpperCase().replace(/[\s=]/g, "")) {
    bits += alphabet.indexOf(char).toString(2).padStart(5, "0");
  }
  const key = Buffer.from((bits.match(/.{8}/g) ?? []).map((byte) => parseInt(byte, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(at / 1000 / 30)));
  const digest = createHmac("sha1", key).update(counter).digest();
  const offset = (digest[digest.length - 1] ?? 0) & 0x0f;
  const number =
    (((digest[offset] ?? 0) & 0x7f) << 24) |
    ((digest[offset + 1] ?? 0) << 16) |
    ((digest[offset + 2] ?? 0) << 8) |
    (digest[offset + 3] ?? 0);
  return String((number >>> 0) % 1_000_000).padStart(6, "0");
}
