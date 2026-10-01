import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { fileURLToPath } from "node:url";

const PHOTO = fileURLToPath(new URL("./fixtures/card-disc-5mm.jpg", import.meta.url));

async function accessible(page: Page, name: string) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(blocking.map((v) => `${name}: ${v.id} (${v.nodes.length})`)).toEqual([]);
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
  await page.getByRole("button", { name: "New visit", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Photos", exact: true })).toBeVisible();
  await page.getByLabel("Kind").selectOption("with_reference");
  await page.getByLabel("Choose a file").setInputFiles(PHOTO);
  await expect(page.getByRole("button", { name: /Open the photo/ })).toBeVisible();
  await expect(page.getByText("Checking the photos…")).toHaveCount(0, { timeout: 60_000 });
  await accessible(page, "visit");

  await page.getByRole("link", { name: "Measure on the photo", exact: true }).click();
  await expect(page.getByText(/Reference card found/)).toBeVisible({ timeout: 60_000 });
  await accessible(page, "measure");
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

  await page.getByRole("link", { name: /Back to Chest mark/ }).click();
  await expect(page.getByText(/Latest size/)).toBeVisible();
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible();
  await accessible(page, "settings");
});
