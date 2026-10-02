import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const PHOTO = fileURLToPath(new URL("./fixtures/card-disc-5mm.jpg", import.meta.url));

async function accessible(page: Page, name: string) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  const where = (v: (typeof blocking)[number]) => v.nodes.map((n) => n.target.join(" ")).join(", ");
  expect(blocking.map((v) => `${name}: ${v.id} at ${where(v)}`)).toEqual([]);
}

/** A visit with a photo of the card, and the 5 mm disc in its window measured. */
async function measuredVisit(page: Page, first: boolean) {
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

/** Screenshots for a human look at layout and both themes, only when asked for. */
async function shot(page: Page, name: string) {
  const dir = process.env.NEVUS_E2E_SHOTS;
  if (!dir) return;
  for (const scheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: scheme });
    await page.waitForTimeout(400); // let colour transitions finish
    await page.screenshot({ path: `${dir}/${name}-${scheme}.png`, fullPage: true });
  }
  await page.emulateMedia({ colorScheme: "light" });
}

test("from a fresh instance to a measured mark, accessibly", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Claim this instance", exact: true })).toBeVisible();
  await accessible(page, "claim");
  await page.getByLabel("Username").fill("Jose");
  await page.getByLabel("Password", { exact: true }).fill("correct horse battery");
  await page.getByLabel("Repeat the password").fill("correct horse battery");
  await page.getByRole("button", { name: "Create the administrator", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Persons", exact: true })).toBeVisible();
  await accessible(page, "home");
  await page.getByRole("button", { name: "Add a person", exact: true }).click();
  await page.getByLabel("Name", { exact: true }).fill("Ana");
  await page.getByRole("button", { name: "Create", exact: true }).click();
  await page.getByRole("link", { name: /Ana/ }).click();

  await expect(page.getByRole("heading", { name: "Body map", exact: true })).toBeVisible();
  await accessible(page, "person");
  await page.getByRole("button", { name: "Add a mark", exact: true }).click();
  await page.getByRole("button", { name: "Right pectoral", exact: true }).click();
  await page.getByLabel("Name", { exact: true }).fill("Chest mark");
  await page.getByRole("button", { name: "Create the mark", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Chest mark", exact: true })).toBeVisible();
  await accessible(page, "mark");
  await measuredVisit(page, true);
  await page.getByRole("link", { name: /Back to Chest mark/ }).click();
  await expect(page.getByText(/Latest size/)).toBeVisible();

  // A second visit: the size over time appears, and the two visits can be compared.
  await measuredVisit(page, false);
  await page.getByRole("link", { name: /Back to Chest mark/ }).click();
  const chart = page.getByRole("slider", { name: /Longest diameter at 2 visits/ });
  await expect(chart).toBeVisible();
  await accessible(page, "mark with a chart");
  await chart.focus();
  await page.keyboard.press("ArrowLeft");
  await expect(chart).toHaveAttribute("aria-valuenow", "1");
  await shot(page, "mark");
  await page.getByRole("link", { name: "Compare visits", exact: true }).click();
  await expect(page.getByText("Lined up with the reference card in both photos.")).toBeVisible({
    timeout: 60_000,
  });
  await accessible(page, "compare");
  await shot(page, "compare-side");
  await page.getByRole("radio", { name: "Differences", exact: true }).click();
  await expect(page.getByText(/measures nothing/)).toBeVisible();
  await accessible(page, "compare differences");
  await shot(page, "compare-difference");
  await page.getByRole("radio", { name: "Slider", exact: true }).click();
  await shot(page, "compare-wipe");
  await page.getByRole("link", { name: "Back to the mark", exact: true }).click();
  await expect(chart).toBeVisible();

  // The mark's record as a PDF, rendered by the background worker.
  await page.getByRole("button", { name: "Make the record of this mark", exact: true }).click();
  const pdf = page.getByRole("link", { name: /Download the PDF/ });
  await expect(pdf).toBeVisible({ timeout: 60_000 });
  await accessible(page, "mark with a report");
  const [download] = await Promise.all([page.waitForEvent("download"), pdf.click()]);
  const file = readFileSync(await download.path());
  expect(file.subarray(0, 5).toString()).toBe("%PDF-");
  if (process.env.NEVUS_E2E_SHOTS) await download.saveAs(`${process.env.NEVUS_E2E_SHOTS}/mark-report.pdf`);
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible();
  await accessible(page, "settings");
});
