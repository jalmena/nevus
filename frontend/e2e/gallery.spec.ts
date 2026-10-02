import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { measuredVisit, openTool, PASSWORD, PHOTO, shot, totpCode } from "./helpers";

// Every screen of the app, photographed on each device and in both colour schemes, for a look at the
// design. Not a test of behaviour: the journey is. `pnpm run shots` runs it and makes contact sheets.
const DIR = process.env.NEVUS_SHOTS_DIR ?? fileURLToPath(new URL("../.screenshots", import.meta.url));
// With NEVUS_SHOTS_AXE set, every screen is also checked with axe in both colour schemes and the
// findings (every impact, best practices included) are written next to the screenshots: the audit.
const AXE = Boolean(process.env.NEVUS_SHOTS_AXE);

interface Finding {
  screen: string;
  scheme: string;
  id: string;
  impact: string | null | undefined;
  help: string;
  nodes: string[];
}

test("every screen, for a look at the design", async ({ page }, info) => {
  const findings: Finding[] = [];
  const snap = async (name: string) => {
    await shot(page, name, `${DIR}/${info.project.name}`);
    if (!AXE) return;
    for (const scheme of ["light", "dark"] as const) {
      await page.emulateMedia({ colorScheme: scheme });
      await page.waitForTimeout(400); // colours transition; measured mid-way they fail for no reason
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"])
        .analyze();
      for (const violation of results.violations) {
        findings.push({
          screen: name,
          scheme,
          id: violation.id,
          impact: violation.impact,
          help: violation.help,
          nodes: violation.nodes.map((node) => node.target.join(" ")),
        });
      }
    }
    await page.emulateMedia({ colorScheme: "light" });
  };
  const region = (name: string) =>
    page.getByRole("listitem").filter({ has: page.getByRole("heading", { name }) });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Claim this instance", exact: true })).toBeVisible();
  await snap("01-claim");
  await page.getByLabel("Username").fill("Jose");
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByLabel("Repeat the password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create the administrator", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Persons", exact: true })).toBeVisible();
  await snap("02-home-empty");
  await page.getByRole("button", { name: "Add a person", exact: true }).click();
  await page.getByLabel("Name", { exact: true }).fill("Ana");
  await page.getByRole("button", { name: "Create", exact: true }).click();
  await expect(page.getByRole("link", { name: /Ana/ })).toBeVisible();
  await snap("03-home");

  await page.getByRole("link", { name: /Ana/ }).click();
  await expect(page.getByRole("heading", { name: "Body map", exact: true })).toBeVisible();
  await snap("04-person-empty");
  await page.getByRole("button", { name: "Add a mark", exact: true }).click();
  await snap("05-person-placing");
  await page.getByRole("button", { name: "Right pectoral", exact: true }).click(); // zooms in on the zone
  await snap("05b-person-zoomed");
  await page.getByRole("button", { name: "Right pectoral", exact: true }).click(); // places the mark
  await page.getByLabel("Name", { exact: true }).fill("Chest mark");
  await page.getByRole("button", { name: "Create the mark", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Chest mark", exact: true })).toBeVisible();
  await snap("06-mark-empty");
  await measuredVisit(page, false);
  await snap("07-visit");
  await page.getByRole("link", { name: /Back to Chest mark/ }).click();
  await measuredVisit(page, false);
  await page.getByRole("link", { name: /Back to Chest mark/ }).click();
  await expect(page.getByRole("slider", { name: /Longest diameter at 2 visits/ })).toBeVisible();
  await page.getByRole("button", { name: "Make the record of this mark", exact: true }).click();
  await expect(page.getByRole("link", { name: /Download the PDF/ })).toBeVisible({ timeout: 60_000 });
  await snap("08-mark");
  await page.getByRole("link", { name: "Compare visits", exact: true }).click();
  await expect(page.getByText("Lined up with the reference card in both photos.")).toBeVisible({
    timeout: 60_000,
  });
  await snap("09-compare-side");
  await page.getByRole("radio", { name: "Differences", exact: true }).click();
  await expect(page.getByText(/measures nothing/)).toBeVisible();
  await snap("10-compare-difference");
  await page.getByRole("radio", { name: "Slider", exact: true }).click();
  await snap("11-compare-wipe");

  await page.getByRole("link", { name: "Persons", exact: true }).click();
  await page.getByRole("link", { name: /Ana/ }).click();
  await expect(page.getByRole("heading", { name: "Full-body sessions", exact: true })).toBeVisible();
  await snap("12-person");
  await openTool(page, "sessions", "Full-body sessions");
  await page.getByRole("button", { name: "Start a session", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: /^Session of/ })).toBeVisible();
  const firstSession = page.url();
  await region("Chest and shoulders").getByLabel("Take the photo").setInputFiles(PHOTO);
  await expect(region("Chest and shoulders").getByText("0 marks")).toBeVisible({ timeout: 30_000 });
  await region("Abdomen and pelvis").getByRole("button", { name: "Skip", exact: true }).click();
  await expect(region("Abdomen and pelvis").getByText("Skipped", { exact: true })).toBeVisible();
  await snap("13-session");
  await region("Chest and shoulders")
    .getByRole("link", { name: "Open the photo of Chest and shoulders" })
    .click();
  const canvas = page.getByRole("application", { name: "Photo of Chest and shoulders" });
  await expect(canvas).toBeVisible();
  const box = await canvas.boundingBox();
  if (!box) throw new Error("no canvas");
  await page.mouse.click(box.x + box.width * 0.3, box.y + box.height * 0.4);
  await expect(page.getByRole("region", { name: "The mark you tapped" })).toBeVisible();
  await snap("14-session-zone-tapped");
  await page
    .getByRole("region", { name: "The mark you tapped" })
    .getByRole("button", { name: "Link to it" })
    .click();
  await expect(page.getByRole("button", { name: /1\. Chest mark/ })).toBeVisible();
  await page.getByRole("button", { name: /1\. Chest mark/ }).click();
  await snap("15-session-zone");
  await page.getByRole("button", { name: "Blur a part of the photo", exact: true }).click();
  const area = await canvas.boundingBox(); // the page may have scrolled since the box above was measured
  if (!area) throw new Error("no canvas");
  await page.mouse.click(area.x + area.width * 0.55, area.y + area.height * 0.55);
  await page.mouse.click(area.x + area.width * 0.9, area.y + area.height * 0.9);
  await expect(page.getByRole("button", { name: "Blur 1 area", exact: true })).toBeEnabled();
  await snap("15b-session-zone-blur");
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await page.getByRole("link", { name: "Back to the session", exact: true }).click();
  await page.getByRole("button", { name: "Finish the session", exact: true }).click();
  await expect(page.getByText(/^Finished/)).toBeVisible();
  await page.getByRole("link", { name: "Back to the person", exact: true }).click();
  await openTool(page, "sessions", "Full-body sessions");
  await page.getByRole("button", { name: "Start a session", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: /^Session of/ })).toBeVisible();
  await expect(page).not.toHaveURL(firstSession);
  await region("Chest and shoulders").getByLabel("Take the photo").setInputFiles(PHOTO);
  await expect(region("Chest and shoulders").getByText("0 marks")).toBeVisible({ timeout: 30_000 });
  await page.getByRole("link", { name: "Back to the person", exact: true }).click();
  await page.getByRole("link", { name: "Compare the last two sessions", exact: true }).click();
  await expect(page.getByRole("radiogroup")).toBeVisible();
  await snap("16-sessions-compare");

  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Settings", exact: true })).toBeVisible();
  await snap("17-settings");
  await page.getByRole("button", { name: "Set up a second factor", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await snap("18-sudo");
  await dialog.getByLabel("Password").fill(PASSWORD);
  await dialog.getByRole("button", { name: "Confirm", exact: true }).click();
  const shown = await page.getByText(/^[A-Z2-7]{4}( [A-Z2-7]{4})+$/).textContent();
  const secret = (shown ?? "").replace(/\s/g, "");
  await snap("19-settings-second-factor");
  await page.getByLabel("Code the app shows now").fill(totpCode(secret));
  await page.getByRole("button", { name: "Turn the second factor on", exact: true }).click();
  await expect(page.getByRole("region", { name: "Recovery codes" })).toBeVisible();
  await snap("20-settings-recovery-codes");
  await page.getByRole("button", { name: "I have saved them", exact: true }).click();
  await page.getByRole("link", { name: /Evaluation set/ }).click();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await snap("21-evaluation");
  await page.goto("/trash");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await snap("22-trash");

  await page.goto("/settings");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Sign in", exact: true })).toBeVisible();
  await snap("23-login");
  await page.getByLabel("Username").fill("Jose");
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "One more step", exact: true })).toBeVisible();
  await snap("24-login-code");
  await page.getByRole("button", { name: "Use a recovery code instead", exact: true }).click();
  await snap("25-login-recovery");

  if (AXE) {
    mkdirSync(DIR, { recursive: true });
    writeFileSync(`${DIR}/a11y-${info.project.name}.json`, JSON.stringify(findings, null, 2));
  }
});
