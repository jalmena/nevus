# neVus — Third pass evaluation

Design review of the third pass as implemented on `feature/design-pass-3`, written 2026-10-14 against `REDESIGN_SPEC.md` §8 (ten criteria, 0–3 each, 30 in total; a screen passes at 24 or more with no criterion at 0). Judged from `frontend/.screenshots/{phone,desktop,tablet}/*-light.png` (phone = Pixel 7, 412 CSS px, device pixels at 2.625×; desktop 1280 × 900; tablet 820) with the dark variants and the tablet spot-checked, and the rejected gallery in `.screenshots/sheets/` used only for the before/after.

Two reading conventions. First, the captures are full-page with the sticky bars flattened, so the phone's first viewport is the top 2202 device px (≈ 839 CSS px) and the bottom bar is assumed fixed at the bottom of it. Second, criterion 5 ("the photograph or the map is the hero") is written for canvas pages; on a list or form page I score it on whether the thing the user came for is what the first viewport shows, undecorated — a 3 means nothing competes with it.

## 1. Verdict in one paragraph

The gallery reads as one quiet application. The structure the specification asked for is there on every screen: a 56 px app bar with a chevron, a title and at most two icons plus a menu; content as rows with hairlines; one filled primary in the bottom bar or the app bar; sheets and dialogs for forms; group labels in settings; a rail with a context block on the desktop. Next to the rejected sheets (brand block, underlined "Back", fourteen cards, thirty-eight buttons on the session page) this is a different product, and it is the product the brief describes: sober, elegant, simple. What remains is a second-order list — spacing, copy length, date formats, four alignment defects and three genuine bugs — and it is concentrated in the same handful of patterns, so a short pass lifts most screens at once. Pass rate: **60 of 62 screens** (phone 29/31, desktop 31/31); mean score 26.7 on the phone and 28.1 on the desktop.

## 2. Scores

| Screen | Device | c1 | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | c10 | Total | Pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 01 claim | phone | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 30 | yes |
| 01 claim | desktop | 2 | 3 | 3 | 3 | 3 | 3 | 1 | 3 | 3 | 3 | 27 | yes |
| 02 home, empty | phone | 2 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 29 | yes |
| 02 home, empty | desktop | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 30 | yes |
| 03 home | phone | 2 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 29 | yes |
| 03 home | desktop | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 29 | yes |
| 04 person, empty | phone | 1 | 3 | 3 | 3 | 2 | 3 | 2 | 3 | 2 | 3 | 25 | yes |
| 04 person, empty | desktop | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 2 | 3 | 28 | yes |
| 05 person, placing | phone | 1 | 2 | 3 | 3 | 2 | 2 | 2 | 3 | 2 | 3 | 23 | **no** |
| 05 person, placing | desktop | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 2 | 3 | 28 | yes |
| 05b person, zoomed | phone | 2 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 28 | yes |
| 05b person, zoomed | desktop | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 29 | yes |
| 05c new mark sheet | phone | 2 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 28 | yes |
| 05c new mark sheet | desktop | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 29 | yes |
| 06 mark, empty | phone | 2 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 29 | yes |
| 06 mark, empty | desktop | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 29 | yes |
| 07 visit | phone | 2 | 3 | 3 | 3 | 2 | 3 | 2 | 2 | 3 | 3 | 26 | yes |
| 07 visit | desktop | 3 | 2 | 3 | 3 | 2 | 3 | 3 | 2 | 3 | 3 | 27 | yes |
| 08 mark | phone | 2 | 3 | 3 | 2 | 3 | 3 | 2 | 3 | 3 | 3 | 27 | yes |
| 08 mark | desktop | 3 | 3 | 3 | 2 | 2 | 3 | 2 | 2 | 3 | 3 | 26 | yes |
| 08b mark reports | phone | 2 | 3 | 3 | 3 | 3 | 2 | 2 | 3 | 3 | 3 | 27 | yes |
| 08b mark reports | desktop | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 2 | 3 | 3 | 28 | yes |
| 09 compare, side by side | phone | 2 | 3 | 3 | 2 | 2 | 3 | 2 | 3 | 3 | 3 | 26 | yes |
| 09 compare, side by side | desktop | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 3 | 3 | 29 | yes |
| 10 compare, differences | phone | 2 | 3 | 3 | 2 | 2 | 3 | 2 | 3 | 2 | 3 | 25 | yes |
| 10 compare, differences | desktop | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 29 | yes |
| 11 compare, slider | phone | 2 | 3 | 3 | 2 | 2 | 3 | 2 | 3 | 2 | 3 | 25 | yes |
| 11 compare, slider | desktop | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 29 | yes |
| 12 person | phone | 1 | 3 | 3 | 3 | 2 | 3 | 2 | 3 | 2 | 3 | 25 | yes |
| 12 person | desktop | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 29 | yes |
| 12b person sessions | phone | 2 | 3 | 3 | 3 | 3 | 2 | 2 | 3 | 3 | 3 | 27 | yes |
| 12b person sessions | desktop | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 3 | 29 | yes |
| 13 session | phone | 2 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 1 | 3 | 26 | yes |
| 13 session | desktop | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 29 | yes |
| 14 zone, tapped | phone | 2 | 3 | 3 | 3 | 2 | 2 | 3 | 3 | 3 | 3 | 27 | yes |
| 14 zone, tapped | desktop | 3 | 3 | 3 | 3 | 2 | 2 | 3 | 3 | 3 | 3 | 28 | yes |
| 15 zone | phone | 2 | 3 | 3 | 3 | 2 | 2 | 1 | 3 | 3 | 3 | 25 | yes |
| 15 zone | desktop | 3 | 3 | 3 | 3 | 2 | 2 | 1 | 3 | 3 | 3 | 26 | yes |
| 15b zone, blur | phone | 1 | 3 | 3 | 3 | 2 | 1 | 1 | 3 | 3 | 3 | 23 | **no** |
| 15b zone, blur | desktop | 3 | 3 | 3 | 3 | 2 | 2 | 1 | 3 | 3 | 3 | 26 | yes |
| 16 sessions compare | phone | 2 | 3 | 3 | 2 | 2 | 3 | 2 | 3 | 2 | 3 | 25 | yes |
| 16 sessions compare | desktop | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 2 | 3 | 28 | yes |
| 17 settings | phone | 2 | 3 | 3 | 3 | 3 | 3 | 2 | 2 | 3 | 3 | 27 | yes |
| 17 settings | desktop | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 29 | yes |
| 17b reminders | phone | 2 | 3 | 3 | 3 | 3 | 2 | 2 | 3 | 2 | 3 | 26 | yes |
| 17b reminders | desktop | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 3 | 28 | yes |
| 18 sudo | phone | 2 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 28 | yes |
| 18 sudo | desktop | 3 | 2 | 3 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 28 | yes |
| 19 second factor set-up | phone | 2 | 3 | 2 | 3 | 3 | 2 | 2 | 2 | 3 | 3 | 25 | yes |
| 19 second factor set-up | desktop | 3 | 2 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 3 | 27 | yes |
| 20 recovery codes | phone | 2 | 2 | 2 | 3 | 3 | 1 | 2 | 3 | 3 | 3 | 24 | yes |
| 20 recovery codes | desktop | 3 | 2 | 2 | 3 | 3 | 2 | 3 | 3 | 3 | 3 | 27 | yes |
| 21 evaluation set | phone | 2 | 3 | 3 | 3 | 2 | 2 | 2 | 3 | 3 | 3 | 26 | yes |
| 21 evaluation set | desktop | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 3 | 29 | yes |
| 22 trash | phone | 2 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 29 | yes |
| 22 trash | desktop | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 30 | yes |
| 23 sign in | phone | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 30 | yes |
| 23 sign in | desktop | 2 | 3 | 3 | 3 | 3 | 3 | 1 | 3 | 3 | 3 | 27 | yes |
| 24 sign in, code | phone | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 30 | yes |
| 24 sign in, code | desktop | 2 | 3 | 3 | 3 | 3 | 3 | 1 | 3 | 3 | 3 | 27 | yes |
| 25 sign in, recovery | phone | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 3 | 3 | 29 | yes |
| 25 sign in, recovery | desktop | 2 | 3 | 3 | 3 | 3 | 2 | 1 | 3 | 3 | 3 | 26 | yes |

Lowest criterion across the gallery: **c1** on the phone (2 on 24 screens, 1 on 4), then **c7** (2 on 30 screens, 1 on 7), then **c6** and **c5** on the canvas pages. c2, c3, c4, c8 and c10 are essentially solved: the action policy, the rows and the calm are in.

## 3. Fixes, grouped by pattern, ranked by how many screens they lift

**F1 · Header-to-content gap (every interior phone screen; c1).** The `h1` sits ~75 px below the top and the first content ~70 px below the meta line, so rows, photographs and sentences begin at 150–230 px instead of the 140 px the rubric asks for (home: empty sentence at 190; settings: first row at 185; compare: photographs at 230). Fix: header block `margin-bottom: var(--space-6)` (24 px) instead of the current ~64–72 px, and `h1 margin-top: var(--space-4)`. This alone moves c1 from 2 to 3 on about twenty phone screens.

**F2 · Person page map on the phone (04, 05, 05b, 05c, 12; c1, c5, c7).** The silhouette is cut at the shins in the first viewport and the feet sit under the bottom bar; the spec's height `calc(100dvh − 56px − 44px − 24px − 64px − 40px)` is not applied. Also the legend "● tracked ● due" renders with 0 marks. Fix: apply the formula to the map container with `object-fit: contain`; hide the legend when the person has no marks; while placing, the bar's instruction is one line ("Tap the zone where the mark is.") and the second sentence appears after the zoom, so the bar stays 64 px (today it grows to three lines, ~100 px).

**F3 · Quiet buttons inset from the text edge (05c, 08b, 10, 12b, 15b, 17b, 18, 19, 20, 21; c7).** "Learn more" and "Suggest a name" carry the button's 16 px horizontal padding, so their text starts 16 px right of the column. Fix: an inline variant of the quiet button with `margin-inline-start: calc(-1 * var(--space-3))`, or no horizontal padding when it stands alone under a sentence.

**F4 · Sub-page intros are descriptions, not status (08b, 12b, 17b, 18, 19, 20, 21, both devices; c6).** "The PDF record of this mark for the clinician.", "The whole body, region by region, to compare over time.", "A code from your phone, besides the password." sit under the title in addition to the status line, and 12b's empty state repeats the intro almost verbatim. Fix per §6.3: keep the status line only, move the description into the Learn more sheet; on 12b drop the intro and keep the empty-state sentence.

**F5 · Helpers over two lines or 90 characters (05, 14, 15, 15b, 20, 25; c6).** Zone hint "Tap the photo where a mark is, then link it to a mark you already follow or record it as a new one." (≈100), blur hint (134, three lines on the phone), recovery codes paragraph (three lines), recovery sign-in intro (96, three lines). Fix: the spec's rewrites — "Tap a mark on the photo to record it.", "Tap two opposite corners of the area to blur." with "Replaces the photo for good; the marks stay." under the toolbar, "Each signs you in once if the phone is lost. They are not shown again." (69), "Enter a recovery code you saved. Each works once." (49).

**F6 · One date format (07, 08, 08b, 12, 13, 16, 21; c7).** The mark page alone shows "October 13, 2026", "Oct 13, 2026", "Oct 13" and "Jan 11, 2027". Fix: one absolute format everywhere, `d MMM yyyy` ("13 Oct 2026"), the chart axis "13 Oct", the visit and session `h1` "13 Oct 2026" / "Session · 13 Oct 2026", the sessions-compare `h1` "Two sessions" with meta "12 Jun and 5 Oct 2026" (today the title wraps to two lines on the phone).

**F7 · Compare pages on the phone (09, 10, 11, 16; c4, c5, c7, c9).** Picker buttons truncate ("Oct 13 · Wi…"); photographs sit in 16 px gutters with a 12 px radius instead of edge to edge; the mode control moves between modes (above the legend in Differences, below the slider in Slider); the slider's label "Where the later photo starts" is set at 500 weight and reads as a heading. Fix: label the pickers "Earlier · 13 Oct" (kind in the sheet, not the button); photographs full-bleed with no radius below 900 px; mode control always directly under the photographs, then slider or legend, then the caption; slider label at `--text-sm` 400 ink-2. On the desktop let the compare and sessions-compare pages use the 72 rem content width so each photograph reaches ~500 px (today two 346 px photographs sit in a 44 rem column with 300 px of empty paper to their right).

**F8 · Sign-in family on the desktop (01, 23, 24, 25; c7).** The 22 rem form is left-aligned at the 16 px gutter and 672 px wide while the tagline is centred. Fix per §5.12: `max-width: 22rem; margin-inline: auto`, top third.

**F9 · Zone pages (14, 15, 15b; c7).** The mark row's 48 px crop is blank white (the crop is offset off the mark); the meta repeats the title ("1. Chest mark / Chest mark"); the canvas has a 1 px ink border the spec does not have. Fix: crop centred on the mark's point; meta "found again" / "linked" / "no clear spot found"; drop the border, the photo-frame colour is enough.

**F10 · Disabled and hover states (04, 05, 12, 16, 17b, 19; c9).** Zoom-out is drawn at 0.45 at rest on every person page; the help IconButton's hover is a rounded square while the back button's is a circle (confirmed at 1:1 on 08 and 16); the desktop copy control on 19 is a bordered square, a sixth shape; the reminders switch rests disabled. Fix: one hover/focus shape (40 px circle) for every IconButton including the copy control; hide zoom-out at minimum zoom rather than disabling it; the reminders switch enabled with the hint explaining what turning it on needs.

**F11 · Settings (17; c7, c8).** The phone app bar shows the inline mark where the back chevron belongs, so there is no way back but the browser; an "Appearance ▸" row sits above the same three Appearance rows inline; the group label "Reminders" sits over a row titled "Reminders" and "Your data" over "Your data"; the Language and Theme selects have different widths. Fix: back chevron labelled "Back to persons"; remove the Appearance row; label the groups "Account", "Reminders and notifications", "Security", "Measuring", "Data", "Administration"; selects at one fixed width (12 rem). On the desktop "Notifications on this device" wraps in the rail; "Notifications" fits.

**F12 · Visit page (07; c5, c7, c8).** The add tile is a bare "+" instead of the `camera` icon with "Add a photo"; the measurement meta wraps under the trailing trash icon; on the desktop "Measure" appears twice (app bar and section header) and the photograph takes 510 px of a 1040 px content area with the lower half of the page empty. Fix: camera tile with its label; meta truncated with the trash in the row's trailing slot; keep "Measure" only in the section header once a measurement exists; photograph at 60 % of the content width on the desktop.

**F13 · Mark page (08; c4, c5, c7, c8).** The chart sits in a bordered, rounded card; on the desktop the download control is icon-only next to "Show as a table" with its label, and the whole page is a single 44 rem column with the chart below the fold. Fix: chart with hairlines above and below, no card; "Download as CSV" label on the desktop; two panes from 900 px (visits left, size over time right) as the spec draws.

**F14 · Primary placement on the security pages (19, 20; c2, c3).** Recovery codes: "I have saved them" and "Save as a file" are right-aligned in the content column, not in the bottom bar / app bar; second-factor set-up: the copy control floats alone under the secret on the phone. Fix: primary in the bar, "Save as a file" as the section's `download` IconButton with label; the secret as a row with `copy` trailing.

**F15 · Session page (13; c7, c9).** The selected row's background uses a negative margin wider than the page gutter and overflows the viewport by ~11 CSS px (the capture is 1110 device px wide: the page scrolls horizontally); the current region appears twice ("Face" card and highlighted "Face" row); row metas mix "not yet", "Skipped", "0 marks". Fix: `margin-inline: calc(-1 * var(--space-3))` with matching padding and `overflow-x: clip` on the list; card title "Next: Face" and no row highlight (or the highlight and no card title); metas in sentence case throughout.

**F16 · Sudo on the desktop (18; c2, c9).** While the password dialog is open the page's primary in the app bar reads "Working…" at 0.45 opacity, as if the app were stuck. Fix: the primary keeps its label until the password is confirmed; "Working…" only after submission.

**F17 · Home row (03; c7).** The person row shows the role as trailing text and no chevron, so it does not read as navigable. Fix per §4.5: role as the meta line, `chevron-right` trailing.

**F18 · Gallery captures (05, 07, 13 and the hover states).** Three frames show the app bar in the middle of the page because the page was scrolled when the sticky bar was flattened; the pointer rests on a segment ("Head" on phone and tablet, "Hands" on desktop) and on the back or help button, so hover states are baked into 04, 08, 12, 16; the rail is 100 vh tall, so on pages taller than 900 px it ends mid-page. Fix in the shot script: scroll to top and move the pointer off-page before capture; rail `min-height: 100%` of the layout rather than `100vh`.

## 4. Broken, misaligned, truncated or off-spec (beyond the rubric)

- Session page horizontal overflow on the phone and tablet (F15) — a real bug, visible as a sideways scroll.
- Zone mark crop blank (F9) — a real bug; the user sees a white square where the mark should be.
- Desktop sign-in, claim and second-factor forms left-aligned (F8) — the only composition defect that reads as unfinished.
- Compare picker labels truncated on the phone (F7).
- Session title / selected row overflow and duplicate "Face" (F15).
- Rail context block absent on the mark and visit pages (06, 07, 08) but present on reports and sessions (08b, 12b): inside a person every page should show the context block (§4.1).
- Settings reached on the phone without a back chevron (F11).
- Recovery codes and second-factor primaries in the content column (F14), against §4.3 "one primary … bottom bar / app bar".
- Measure page (§5.5) is not in the gallery and could not be scored.
- "Turn the second factor on" is five words; §6.6 allows it only because the spec itself proposes it — "Turn it on" would do.
- Dark mode: checked on 07, 08, 17, 23; tokens hold, the lighter accent on dark paper is right, the chart card border is visible, nothing broken. The sign-in brand block merges with the dark page, which is acceptable.
- Tablet (820): behaves as the wide phone the spec asks for; the whole silhouette fits the first viewport there, which confirms the phone problem is the missing height formula, not the drawing.

## 5. Verdict

**Does it read as one quiet application?** Yes. The contact sheets show the same silhouette on every page: chevron, title, a line of meta, rows, one teal button. Nothing shouts; the amber appears only on the quality icon and the due dot; red appears nowhere. The three canvas treatments (body map, photograph, compare) sit inside the same shell without a visible seam, and the sheets and dialogs are the only boxes left. Measured against the Product Owner's words — modern, sober, elegant, simple, intuitive, no buttons cluttering the page, information well organised, icons or text as each case needs — the pass answers every one of them; the mark, session and settings pages are the clearest proof against their rejected versions.

**Strongest screens.** The sign-in family on the phone (30, 30, 30, 29), home and trash (29–30), the mark page on the desktop (the facts strip, the visit rows and the section icons are exactly the spec's wireframe), the session page on the desktop (rows left, current region right, three controls in the bar), the settings list on both devices.

**Weakest screens.** Phone 05 person placing (23 — silhouette cut, three-line bar, and the gallery frame itself is broken), phone 15b zone blur (23 — three-line hint, blank crop, duplicate meta), phone 20 recovery codes (24 — three-line paragraph and two buttons in the content column). Behind them, every page built on the person map on the phone (04, 12 at 25) for the same single reason.

**What to do next, in order.** F1 and F2 first (they touch twenty-five phone screens and the hub of the app); then F3–F6 as one copy-and-spacing pass; then the four bugs (F8, F9, F15, F16); then the page-specific items. After F1–F6 I would expect the phone mean to move from 26.7 to about 28.5 and no screen below 26. The gallery should be re-shot with F18 applied before the next review so that hover states and scrolled bars stop costing points that the code did not lose.
