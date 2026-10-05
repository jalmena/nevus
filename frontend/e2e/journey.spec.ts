import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { accessible, measuredVisit, openTool, PASSWORD, PHOTO, shot, signIn, totpCode } from "./helpers";

test("from a fresh instance to a measured mark, accessibly", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Claim this instance", exact: true })).toBeVisible();
  await accessible(page, "claim");
  await page.getByLabel("Username").fill("Jose");
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByLabel("Repeat the password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create the administrator", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Persons", exact: true })).toBeVisible();
  await accessible(page, "home");
  await page.getByRole("button", { name: "Add a person", exact: true }).click();
  await page.getByLabel("Name", { exact: true }).fill("Ana");
  await page.getByRole("button", { name: "Create", exact: true }).click();
  await page.getByRole("link", { name: /Ana/ }).click();

  await expect(page.getByRole("heading", { name: "Body map", exact: true })).toBeVisible();
  await accessible(page, "person");
  await shot(page, "person");
  await page.getByRole("button", { name: "Add a mark", exact: true }).click();
  await page.getByRole("button", { name: "Right pectoral", exact: true }).click(); // zooms in on the zone
  await page.getByRole("button", { name: "Right pectoral", exact: true }).click(); // places the mark
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
  // Both measurements carry shape and colour descriptors, so the chart offers them too.
  await page.getByRole("radio", { name: "Compactness", exact: true }).click();
  await expect(page.getByRole("slider", { name: /Compactness at 2 visits/ })).toBeVisible();
  await page.getByRole("radio", { name: "Longest diameter", exact: true }).click();
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
  await openTool(page, "mark-reports", "Reports");
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
  await expect(page.getByRole("heading", { name: /Notifications on this device/ })).toBeVisible();
  await accessible(page, "settings");
});

test("a full-body session: regions photographed or skipped, a mark pointed at, accessibly", async ({
  page,
}) => {
  await signIn(page);
  const person = page.getByRole("link", { name: /Ana/ });
  if ((await person.count()) === 0) {
    await page.getByRole("button", { name: "Add a person", exact: true }).click();
    await page.getByLabel("Name", { exact: true }).fill("Ana");
    await page.getByRole("button", { name: "Create", exact: true }).click();
  }
  await person.first().click();
  await openTool(page, "sessions", "Full-body sessions");
  await page.getByRole("button", { name: "Start a session", exact: true }).click();

  await expect(page.getByRole("heading", { level: 1, name: /^Session of/ })).toBeVisible();
  await accessible(page, "session");
  const chest = page
    .getByRole("listitem")
    .filter({ has: page.getByRole("heading", { name: "Chest and shoulders" }) });
  await chest.getByLabel("Take the photo").setInputFiles(PHOTO);
  await expect(chest.getByText("0 marks")).toBeVisible({ timeout: 30_000 });
  const abdomen = page
    .getByRole("listitem")
    .filter({ has: page.getByRole("heading", { name: "Abdomen and pelvis" }) });
  await abdomen.getByRole("button", { name: "Skip", exact: true }).click();
  await expect(abdomen.getByText("Skipped", { exact: true })).toBeVisible();
  await expect(page.getByText(/1 of 18 regions photographed/)).toBeVisible();
  await shot(page, "session");

  await chest.getByRole("link", { name: "Open the photo of Chest and shoulders" }).click();
  const canvas = page.getByRole("application", { name: "Photo of Chest and shoulders" });
  await expect(canvas).toBeVisible();
  const box = await canvas.boundingBox();
  if (!box) throw new Error("no canvas");
  await page.mouse.click(box.x + box.width * 0.3, box.y + box.height * 0.4);
  const chooser = page.getByRole("region", { name: "The mark you tapped" });
  await expect(chooser).toBeVisible();
  await accessible(page, "zone");
  await chooser.getByLabel("Name (optional)").fill("Below the collarbone");
  await chooser.getByRole("button", { name: "Record a new mark", exact: true }).click();
  await expect(page.getByRole("button", { name: /1\. Below the collarbone/ })).toBeVisible();
  await shot(page, "session-zone");

  await page.getByRole("link", { name: "Back to the session", exact: true }).click();
  await expect(chest.getByText("1 mark", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Finish the session", exact: true }).click();
  await expect(page.getByText(/^Finished/)).toBeVisible();
});

test("the second factor: set up in the settings, then a sign-in that needs the code", async ({ page }) => {
  await signIn(page);
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await openTool(page, "second-factor", "Second factor");
  await page.getByRole("button", { name: "Set up a second factor", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Password").fill(PASSWORD);
  await dialog.getByRole("button", { name: "Confirm", exact: true }).click();
  const shown = await page.getByText(/^[A-Z2-7]{4}( [A-Z2-7]{4})+$/).textContent();
  const secret = (shown ?? "").replace(/\s/g, "");
  expect(secret.length).toBeGreaterThanOrEqual(32);
  await accessible(page, "second factor setup");
  await shot(page, "settings-second-factor");
  await page.getByLabel("Code the app shows now").fill(totpCode(secret));
  await page.getByRole("button", { name: "Turn the second factor on", exact: true }).click();
  const codes = page.getByRole("region", { name: "Recovery codes" });
  await expect(codes.getByRole("listitem")).toHaveCount(10);
  const recovery = (await codes.getByRole("listitem").first().textContent()) ?? "";
  await accessible(page, "recovery codes");
  await shot(page, "settings-recovery-codes");
  await codes.getByRole("button", { name: "I have saved them", exact: true }).click();
  await expect(page.getByText("The second factor is on. 10 recovery codes left.")).toBeVisible();

  // Signing in now needs the code; a wrong one is refused, the next step's accepted.
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
  await page.getByLabel("Username").fill("Jose");
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "One more step", exact: true })).toBeVisible();
  await accessible(page, "second factor sign-in");
  await shot(page, "login-code");
  await page.getByLabel("Code from the authenticator").fill("000000");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText("Wrong code.");
  await page.getByLabel("Code from the authenticator").fill(totpCode(secret, Date.now() + 30_000));
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Persons", exact: true })).toBeVisible();

  // A recovery code opens the door too, once.
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  // The settings page has a "Username" field of its own (new accounts): wait for the sign-in page.
  await expect(page.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
  await page.getByLabel("Username").fill("Jose");
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("button", { name: "Use a recovery code instead", exact: true }).click();
  await page.getByLabel("Recovery code").fill(recovery);
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Persons", exact: true })).toBeVisible();

  // Leave the account as the other tests expect it.
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await openTool(page, "second-factor", "Second factor");
  await expect(page.getByText("The second factor is on. 9 recovery codes left.")).toBeVisible();
  await page.getByRole("button", { name: "Turn it off", exact: true }).click();
  await dialog.getByLabel("Password").fill(PASSWORD);
  await dialog.getByRole("button", { name: "Confirm", exact: true }).click();
  await openTool(page, "second-factor", "Second factor");
  await expect(page.getByRole("button", { name: "Set up a second factor", exact: true })).toBeVisible();
});
