# neVus — Redesign specification (third pass)

Written 2026-10-06 from the three-device screenshot gallery (`frontend/.screenshots/sheets/`, 27 screens × phone 390 / tablet 820 / desktop 1280), the brief, the two review passes, the tokens, the English catalogue and the page components. It is an independent pass: where it overturns a rule of `DESIGN_REVIEW.md` it says so and why. It is written for the engineer who will build it; nothing here needs a follow-up question to the designer.

Two primitives already exist and are assumed throughout: **IconButton** (a Lucide icon, an accessible label, an optional visible label that may appear only from 900 px) and **Menu** (one "more" button that opens a keyboard-walkable list of actions, with optional icons and a danger style).

---

## 1. Brief

**What the interface must communicate, in three words:** *record, continuity, calm.* A page is a page of a record; time runs through everything; nothing on the screen raises the pulse.

**What it must never suggest:** alarm, a clinic, a verdict. No red for anything but a system error; no words from the forbidden list in `PRODUCT_REQUIREMENTS.md` §7; no element that looks like a diagnosis, a score or a traffic light.

**Fixed decisions kept:**

- The palette exactly as in `tokens.css` (light and dark); no new colour values anywhere. Attention is amber, danger is for system errors and destructive confirmations only.
- Epilogue 400/500/600 with tabular figures; the existing rem scale 0.75 / 0.875 / 1 / 1.125 / 1.375 / 1.75 / 2.25; the existing spacing scale 4…64; radii 6 / 12 / 999.
- Calm, descriptive copy; measurement always with its ± unless the user turns it off; "a documentation aid, never a diagnostic tool".
- WCAG 2.2 AA: 4.5:1 text, 3:1 UI, visible focus ring (`--focus-ring`), 44 × 44 px touch targets, no information carried by colour alone, reduced motion respected.
- Icons from Lucide only (`lucide-react` is already a dependency), 24 px grid, 1.5 px stroke, tinted with the current ink; every icon-only control has an accessible label, and on desktop most carry a visible label.
- The wordmark on dark paper on the sign-in pages, the report and the store card (brief §2). Its use inside the app shell is changed; see §4.1.
- Every capability that exists today stays reachable within two taps of where it is reached today.

**The Product Owner's taste words, verbatim:** "moderno, sobrio y elegante, sencillo e intuitivo, sin botones recargando la página y con la información bien organizada, usando iconos o texto en función de la opción óptima para cada caso". And the verdict this pass answers: "los diseños son pésimos".

**What changes in this round compared with the two declined passes:** the first two passes rearranged the same material (fewer primary buttons, folded tools, two panes). They kept the structure that produces the impression: a tall brand block on every page, a text link for "back", a heading for every section, a card around every list item, every action as a visible button, every explanation as a paragraph. This pass changes that structure.

---

## 2. Diagnosis

Nine patterns make the current screens read as cluttered and dated. Each is named with the screens where it shows; the worst offenders are listed first.

### 2.1 Everything is a box

Every unit of content is wrapped in a bordered, shadowed, rounded card: list items (marks, visits, persons, measurements, webhooks, accounts), disclosures, settings groups, empty states (dashed), the mark panel, the blur panel, the chart. Nothing is figure; everything is frame. On the phone the eye counts boxes before it reads anything.

- **Settings (17, 18, 19, 20)**: 14 cards in a column on all three devices; 6,846 px of scrolling on the phone even after the second pass; on the desktop a 14 rem rail next to a 48 rem column of boxes.
- **Person (4, 5, 5b, 12)**: an empty-state card, a marks card, then five disclosure cards each with a title and a one-line hint. The hub of the app ends with five identical grey boxes.
- **Mark (8)**: two visit cards each holding a 64 px thumbnail and an amber pill, then a chart in a card, then a reports card inside which sits another card (the made report).
- **Session (13)**: eighteen cards.

### 2.2 The first viewport is chrome

On the phone, the dark brand block (96 px), the "Back to the person" link line (≈50 px), the page title (≈60 px) and often an eyebrow or a section heading take 230–300 px of an 844 px viewport before any content appears.

- **Person (4, 5, 12)**: brand block, Back, "Ana · Owner", "Body map", view toggle; the silhouette is cut at the hips and the one primary action ("Add a mark") is below the fold on the 390 × 844 phone. The second pass claimed to have fixed this; the gallery shows it did not.
- **Compare (9, 10, 11)**: brand block, Back, "Compare: Chest mark", two full-width selects, a status line, the mode control, a three-line zoom hint; the photographs begin at the last 60 px of the viewport.
- **Visit (7)**: fine until the photo, then an amber box of five lines pushes everything else down.

### 2.3 The dark brand block on every page

The wordmark on dark paper is right on the sign-in page and the report header. Repeated at 96 px (phone) and 75 px (desktop) on every interior page, it is the heaviest element on every screen, it steals the top of the viewport, and it makes every page open with a black band. "Persons · Settings" as two text links inside it is a website header, not an app bar.

### 2.4 Navigation as underlined links

"Back", "Back to the person", "Back to Chest mark", "Back to the session", "Back to the settings": an underlined teal link above the title on 20 of the 27 screens. It is the single strongest "web page from 2008" signal, and it costs a line. "Compare visits" (mark page) and "Open the trash" (settings) are also underlined links placed as if they were actions.

### 2.5 Every action is a visible button

Counting controls in the first viewport or just under it:

- **Visit (7)**: Kind select, Take a photo, Live camera, Choose a file, Delete (measurement), Measure on the photo, four checkboxes, Save, Move visit to trash. Three equal secondary buttons for one act (adding a photo).
- **Session (13)**: 18 × (Take the photo + Skip or Photograph it after all or Take it again) + Finish the session + Delete the session = 38 buttons; 9,702 px on the phone.
- **Mark (8)**: New visit, Edit details, Compare visits, four metric segments, Show as a table, Download as CSV, two selects, Make the record of this mark, Download the PDF, Delete, Move the mark to the trash.
- **Zone (14, 15, 15b)**: Blur a part of the photo, two selects, Link to it, Record a new mark, Remove from this photo, Cancel; in blur mode three more.
- **Settings (17)**: Sign out, Save, Turn on for this device, Send a test notification visible at once; each folded group adds two to four more.

### 2.6 Explanations treated as content

Instruction paragraphs sit in the content column of almost every page, above the thing they explain, in body size: the session how-to (two lines), the compare zoom hint (three lines on the phone, repeated on three compare screens and on sessions compare), the photo privacy note (three lines), "What you noticed, in your own words. neVus records it and never interprets it.", the reminders intro, the push intro (four lines), the evaluation intro (three lines plus a CLI command in prose), the second-factor intro, the recovery-codes intro, the claim intro (four lines), "A visit is one dated look at the mark…" in the empty state. An app that explains itself on every page reads as a manual.

### 2.7 The photograph is not the hero

- **Visit (7)**: the photo is full width, but it sits inside a tinted frame with a 12 px radius and an amber "!" dot, and is followed at once by the five-line quality notice, the Kind select and three buttons.
- **Compare (9, 10, 11)**: photographs below the fold on the phone (see 2.2).
- **Mark (8)**: the visits show 64 px thumbnails inside cards; the record of a mark is its photographs over time and they are the smallest thing on the page.
- **Zone (14, 15)**: good, the photo leads, but the panel under it is a form of two selects and three buttons.

### 2.8 Too many control shapes

Rectangular buttons at 6 px, a pill segmented control (compare), a card-radius segmented control (body map), pill badges, pill navigation (settings sections on phone), dashed empty states, bordered rows, native selects of two heights, native checkboxes of 22 and 24 px, underlined links, non-underlined quiet buttons, a `details/summary` styled as a link ("How to pose"), a CSS-border chevron. At least eleven distinct interactive shapes. The eye never learns what is tappable.

### 2.9 Weak hierarchy, monotone type, heavy status

Titles at 1.75 rem and section headings at 1.125 rem with everything else at 1 or 0.875 rem gives one level of contrast; labels in ink-3 above values of the same size (facts grid) read as noise. Status is heavy: the filled amber "Quality warnings" pill appears on every visit; the neutral "In 90 days" pill competes with the title; the visit page's title is a timestamp ("October 5, 2026 at 6:00 PM") that names neither mark nor person. On the sign-in pages the only button is drawn at 55 % opacity until the fields are filled, so the first thing a user sees is a broken-looking primary; the sudo dialog does the same.

**What is right and stays:** the palette and its contrast; Epilogue; the silhouette and its zones; the compare and measure tools themselves; the chart with the uncertainty band; the quality flags' wording; the empty-state copy's tone; the brand block on sign-in; the two-pane idea from 900 px.

---

## 3. Three directions

**A. Hub-and-spoke app.** A bottom tab bar on the phone (Persons · Due · Settings) and a left rail on the desktop; each page a screen of an app with a compact top bar of icon actions; the person page the hub.

**B. The record.** A quiet, document-like page: a compact app bar (back, title, at most two icon actions and a "more" menu), content as typographic sections separated by hairlines rather than cards, lists as rows, every occasional tool opened on demand from a row or a menu, the primary action in a bottom bar within the thumb's reach; a left rail on the desktop where the content is wide (settings, person).

**C. Photo-first viewer.** Every page is a canvas (body map or photograph) filling the viewport; all other content and every control live in sheets that slide up over it; actions as icon buttons floating on the canvas.

**Chosen: B, with C as the template for the four canvas pages (placing a mark, measure, compare, session zone).**

Why not A: the information is deep, not wide (persons → person → mark → visit → measure). A tab bar suits wide, shallow apps; here it would take 56 px of every phone viewport, the "Due" tab would duplicate the home page, and the previous pass already found that a bottom bar duplicates what the person page does. Why not C alone: settings, home, the mark's record and the session list are lists and text; sheets over a canvas make them harder, not easier. Why B: it answers every pattern in §2 directly (no brand block, no back link, no cards, no visible-button rows, no explanations in the content column), it is the structure that reads as "sobrio y elegante" at a glance, and it keeps the photograph large on the pages where the photograph matters by giving those pages C's canvas treatment inside B's shell.

---

## 4. The global system

### 4.1 Navigation model

**Phone (< 900 px).**

- **App bar**: 56 px tall, background `--color-paper` (it is part of the page, not a band), a hairline `--color-border` appears only once the page has scrolled. Left: an IconButton `chevron-left` with the accessible label "Back to {parent}" (the catalogue's `*.back*` strings become these labels and stop being visible text). On the home page the left slot holds the inline divider mark (24 px, ink) instead of a back button. Centre-left: the page title at `--text-lg` 600, hidden (visually and `aria-hidden`) while the content's own `h1` is in view, shown once it scrolls out. Right: at most two IconButtons plus the Menu's "more" button (`ellipsis-vertical`, label "More"). Nothing else ever goes in the app bar.
- **No bottom tab bar.** Settings is reached from the home app bar (IconButton `settings`, label "Settings"); from any page it is two taps (back, settings). Persons is the back target of every person page.
- **Bottom action bar**: on pages that have a primary action, a 64 px bar fixed to the bottom (`position: sticky; bottom: 0`, background `--color-surface`, hairline top, `padding-bottom: env(safe-area-inset-bottom)`). It holds the one primary button, full width, and optionally one quiet button to its left (Cancel, Skip). It is the only place a primary button appears on the phone. It is state-dependent: its label and presence follow the page's state (visit: Take a photo → Measure → Save).
- **Sheets**: secondary forms and tool panels open as bottom sheets (`<dialog>` positioned at the bottom, `--radius-card` on the top corners, `--shadow-2`, drag handle 32 × 4 px in `--color-border`, a Close IconButton `x` top-right). A sheet never stacks on a sheet.
- **The dark brand block is removed from the shell** (overturns the implicit rule of the first pass). It stays on sign-in, claim and the second-factor pages, where it frames the entrance as the brief asked, at 120 px wordmark width and 72 px block height.

**Desktop (≥ 900 px).**

- **Left rail**, 240 px, background `--color-surface`, hairline right, full height, sticky. Top: the inline mark (28 px) and "neVus" in Epilogue 600 `--text-lg` as the home link (the B612 wordmark is never set on light paper). Items at 44 px: `users` Persons, `settings` Settings; a hairline; then the **context block**: when inside a person, the person's name as a heading row and under it `person-standing` Body map, `clock` Due & marks (anchors to the right pane), `calendar` Appointments, `scan` Sessions, `file-text` Reports, `calendar-plus` Calendar link, `user` Profile; when inside Settings, the settings sections (§5.11). Rail items show the active one with `--color-accent-2` background and ink text, never accent text on accent background.
- **App bar** on desktop is a 64 px row above the content with the same back / title / actions slots; the primary action moves from the bottom bar into the app bar's right side as a normal primary button with a text label.
- **Content area**: `max-width: 72rem`, `padding: 0 var(--space-6)`. Two panes from 900 px where the page has a canvas: canvas left (sticky), data right. Single text column of `max-width: 44rem` for list pages (home, mark, trash, evaluation) and for every settings section.
- Tablet 600–899 px behaves as a wide phone (single column, bottom bar) — the current gallery at 820 px is consistent with this.

### 4.2 Page header pattern

In the content, in this order, with nothing in between:

1. `h1` at `--text-2xl` (phone) / `--text-3xl` (desktop), weight 600, line height 1.2, `margin-top: var(--space-4)`.
2. One **meta line** at `--text-sm` 400 ink-2, items separated by " · ". It carries what today is spread over an eyebrow, a role badge, a status pill and a facts grid: e.g. mark: "Right pectoral · Front · Mole · next check 3 Jan 2027". A status chip (§4.9) may end the line.
3. Optional **facts strip** when numbers matter (mark: latest size and change), as a two-column `dl` with `dt` at `--text-xs` 600 ink-3 and `dd` at `--text-lg` 600 tabular. Never show a fact whose value is "—": omit the pair.

There is no `h2` "Body map", "Photos", "Visits", "Marks" when the thing under it is self-evident (a silhouette, a photograph, a list of dated rows under a mark). Section headings exist only when a page has two or more peer sections of different kinds (mark: Visits / Size over time / Seen in sessions; visit: Measurements / Notes). An `h2` is `--text-lg` 600 with `margin-top: var(--space-6)`; a section may carry one IconButton at its right (e.g. Size over time: `table` "Show as a table", `download` "Download as CSV").

### 4.3 Action policy

- **One primary per screen**, in the bottom bar (phone) or the app bar (desktop). Its label is a verb phrase of at most three words.
- **Up to two icon actions** in the app bar, for actions used on most visits to the page. They are icon-only on the phone and icon + visible label on the desktop (IconButton's `visibleFrom=900`).
- **Everything else goes into the Menu** ("more"): edit, snooze, reports, export, downloads, rename, and every destructive action (danger style, last, after a separator). A menu item is `icon + text` always.
- **Quiet text buttons** only for Cancel, Skip, Close, "Not now", "Learn more", "Use a recovery code instead".
- **What disappears as a button**: Back (→ app bar icon), Choose a file / Live camera / Kind (→ inside the Add-a-photo sheet), Show as a table / Download as CSV (→ section IconButtons), Compare visits (→ app bar IconButton), Edit details (→ menu), Move … to the trash (→ menu), Delete (measurement / report / webhook rows → row IconButton `trash-2`), Take the photo and Skip on 17 of 18 regions (→ only the current region has them, in the bottom bar), Blur a part of the photo (→ menu), Remove from this photo (→ panel menu), Finish the session / Delete the session (→ menu), Sign out (→ a row in Settings → Account), New recovery codes / Turn it off (→ menu of the Second factor section), Send a test (→ row IconButton `send`).

**Icon table.** Every icon-only control in the interface, with the Lucide name and its label (the label is the `aria-label`; on desktop it is also visible where marked V):

| Use | Lucide | Label | Desktop label |
| --- | --- | --- | --- |
| Back | `chevron-left` | Back to {parent} | icon only |
| Close a sheet or dialog | `x` | Close | icon only |
| More actions | `ellipsis-vertical` | More | icon only |
| Settings (home app bar) | `settings` | Settings | V |
| Add a person (home app bar) | `user-plus` | Add a person | V |
| Add a mark (desktop app bar, phone bottom bar is text) | `plus` | Add a mark | V |
| Zoom in / out / whole body (over the map) | `zoom-in` / `zoom-out` / `expand` | Zoom in / Zoom out / Show the whole body | icon only |
| Compare (mark app bar, when ≥ 2 photographed visits) | `columns-2` | Compare visits | V |
| Edit details (menu) | `pencil` | Edit details | menu |
| Not now / snooze (menu) | `bell-off` | Remind me later | menu |
| Reports (menu, rows) | `file-text` | Reports | menu / row |
| Download (PDF, CSV, codes, card) | `download` | Download {what} | V |
| Show as a table / chart | `table` / `chart-line` | Show as a table / Show as a chart | V |
| Delete a row item (measurement, report, webhook, export) | `trash-2` | Delete {what} | icon only, tooltip |
| Move to trash (menu, danger) | `trash-2` | Move the {mark/visit} to the trash | menu |
| Take a photo (add tile, sheet) | `camera` | Take a photo | V |
| Choose a file (sheet) | `image` | Choose a file | V |
| Live camera (sheet) | `video` | Live camera | V |
| Measure (visit section header) | `ruler` | Measure on the photo | V |
| Outline again / Start again | `rotate-ccw` | Outline again | V |
| Adjust as a circle | `circle` | Adjust as a circle | V |
| Change the scale | `scaling` | Change the scale | V |
| Blur a part of the photo (menu) | `eye-off` | Blur a part of the photo | menu |
| Remove the last area (blur toolbar) | `undo-2` | Remove the last area | V |
| Take it again (zone menu) | `camera` | Take the photo again | menu |
| Link to a mark (panel) | `link` | Link to it | text button |
| Help / about this tool | `circle-help` | About {tool} | icon only |
| Quality note (photo overlay chip) | `triangle-alert` | Quality note: {flags} | chip with text |
| Due (chip) | `clock` | Due | chip with text |
| Send a test (webhook, email, push rows) | `send` | Send a test | V |
| Copy (calendar link, secret) | `copy` | Copy | V |
| Sign out (row) | `log-out` | Sign out | row text |
| Rail: Persons / Settings | `users` / `settings` | — | always text |
| Rail context: Body map / Appointments / Sessions / Reports / Calendar / Profile | `person-standing` / `calendar` / `scan` / `file-text` / `calendar-plus` / `user` | — | always text |
| Settings rows | `user` Account · `palette` Appearance · `bell` Reminders · `smartphone` Notifications on this device · `shield` Second factor · `id-card` Reference card · `database` Your data · `users` Accounts · `mail` Email delivery · `webhook` Webhooks · `archive` Backups · `server` Instance · `info` About | — | row text |

### 4.4 Icon versus text

- **Icon-only is allowed** when the action is universal (back, close, more, add, zoom, settings, download, delete-in-a-row, copy) *and* it sits in a position where that icon is expected (app bar, section header right, row trailing, canvas overlay). Both conditions, or it gets text.
- **Text is required** for every domain action (New visit, Measure, Compare, Take the photo, Finish the session, Link to it, Record a new mark, Use the card). A domain action may carry a leading icon on the desktop; never only an icon.
- **Desktop shows labels**: IconButtons in the app bar and section headers render icon + label from 900 px (`visibleFrom`). Back, Close and More stay icon-only everywhere.
- **Status is text first**: a chip always has words; its icon is decoration (`aria-hidden`). Colour never carries meaning alone.
- **Rows** carry a leading icon only in Settings and the rail (where the icon helps scanning a list of nouns); content rows (marks, visits, persons) carry a thumbnail or an initial, never an icon.
- Tooltips (`title` plus a visible tooltip on hover/focus) on every icon-only control on pointer devices.

### 4.5 Lists and rows

One **Row** pattern for every list in the app, replacing the bordered item cards:

- Height ≥ 56 px with a 48 px leading image, ≥ 48 px without; `padding: var(--space-3) 0`; a hairline `--color-border` between rows, inset to the text start when there is a leading image; no border on the first or last row; no card around the list.
- Leading: a 48 × 48 thumbnail at `--radius-control` on `--color-photo-frame`, or a 40 px circle in `--color-surface-2` with the initial letter (persons), or a Lucide icon (settings).
- Title at `--text-md` 500; one meta line at `--text-sm` 400 ink-2; the meta may hold a chip at its end.
- Trailing: a `chevron-right` in ink-3 when the row navigates; or one control (switch, select, IconButton); or a tabular number/date in ink-2.
- Whole-row hit area is the link or button; hover and focus background `--color-surface-2`.

**Visit rows** (mark page) are the exception that earns more: date as title, then a horizontal strip of up to four 56 px thumbnails, then the meta (photo count · symptoms · quality note with `triangle-alert`). Still no card.

### 4.6 Forms and progressive disclosure

- Fields: label above at `--text-sm` 500, the field 44 px tall, hint under at `--text-xs` ink-2 only when needed; error in `--color-danger` under the field with `role="alert"`. One field shape for text, select and textarea (hairline border, `--radius-control`, surface background).
- Switch (new, S): 44 × 24 track, replaces every settings checkbox; checkboxes remain only inside forms that choose several items (report marks).
- Choice chips (toggle buttons in `role="group"`) replace the four symptom checkboxes and the image kind select.
- Forms that are used once a season (new appointment, report options, calendar link, export) open in a sheet from a row or a menu item; they never sit open on a page.
- Disclosure (`details`) stays only inside sheets and help; it no longer appears on the person page or settings.
- Steps (measure): a two-segment stepper in the app bar subtitle ("1 Scale · 2 Mark"), current in ink, other in ink-3.

### 4.7 Empty states

One sentence of what will appear here and one action; no dashed box, no second heading. Rendered as a block of `--text-md` ink-2 text with `padding: var(--space-6) 0`, and the action is the page's primary (bottom bar on phone), not a second button inside the block. The existing titles become the sentence's start: "No marks yet. Tap the body where the first one is."

### 4.8 Type scale, spacing, dividers

| Role | Size | Weight | Colour |
| --- | --- | --- | --- |
| Page title `h1` | `--text-2xl` phone / `--text-3xl` desktop | 600 | ink |
| App bar title, sheet title | `--text-lg` | 600 | ink |
| Section `h2` | `--text-lg` | 600 | ink |
| Row title, body, buttons | `--text-md` | 500 (buttons 600) | ink |
| Meta, hints, captions | `--text-sm` | 400 | ink-2 |
| Facts labels, chips | `--text-xs` | 600 | ink-3 / chip colour |
| Facts values, measurement readouts | `--text-lg` / `--text-xl` | 600, tabular | ink |

Spacing rhythm: page gutter 16 px (phone) / 24 px (desktop); `h1` to meta 4 px; header to first content 24 px; between sections 32 px; inside a section 12 px; rows 12 px vertical padding. Hairlines (`1px solid --color-border`) separate rows and sections; **cards are reserved for** sheets and dialogs, the current region of a session, and the experimental proposal (dashed `--color-info`). Photographs sit on `--color-photo-frame` with no radius on the phone (edge to edge) and `--radius-card` on the desktop.

### 4.9 Status chips

Pill, `--text-xs` 600, 24 px tall, `padding: 0 var(--space-2)`, optional leading icon 14 px `aria-hidden`:

- **Due** — filled `--color-attention`, text `--color-on-attention`, icon `clock`. The only filled chip.
- **Removed / Resolved** — outline `--color-border`, text ink-2.
- **Experimental** — outline `--color-info`, text ink-2.
- **Quality note** — not a chip in lists: `triangle-alert` 16 px in `--color-attention` plus "quality note" in the meta text. On the photo it is an overlay chip bottom-left (surface background at 90 %, icon + the first flag's word, e.g. "Overexposed") that opens the full note in a sheet.
- "In 90 days" and similar are not chips: they are meta text ("next check 3 Jan").

### 4.10 Destructive actions

Only in a Menu (danger style, last item, after a separator) or as a row-level `trash-2` IconButton for list items that are cheap to restore (measurements, reports, exports, webhooks). Every destructive menu item opens a confirmation dialog: title as the verb ("Move the mark to the trash?"), one sentence of consequence ("Its visits and photos go with it; the trash keeps them for 30 days."), a filled `--color-danger` button with the verb and a quiet Cancel. Overturns the review rule "destructive actions at the end of the page behind a hairline": a red outlined button at the end of every page is still a button on every page.

### 4.11 States

- **Hover** (pointer): rows, quiet and icon buttons, menu items → background `--color-surface-2`; primary → `--shadow-1`; secondary → border `--color-ink-3`.
- **Focus-visible**: `--focus-ring` on every control, including rows, chips, map zones and canvas handles.
- **Active**: segments and rail items → `--color-accent-2` background with ink text (not accent fill), a 2 px accent underline for segments.
- **Disabled**: opacity 0.45, no pointer; **never the resting state of the only primary** (sign-in, sudo, measure save): validate on submit instead.
- **Loading**: skeleton rows of `--color-surface-2`; the bottom-bar button shows "Working…" and stays its size.
- **Pressed / selected marker on the map**: `--color-marker-selected` with a 2 px paper halo.

### 4.12 How many shapes

Five interactive shapes in the whole interface: the **button** (primary filled, secondary outlined, quiet text; one radius, one height), the **icon button** (44 px square hit area, 40 px visible circle on hover), the **chip** (pill, choice or status), the **segmented control** (text segments with an underline, in a hairline-bordered pill only on the desktop; no filled teal segment), and the **field** (text, select, textarea, switch share border, radius and height). Rows and menu items are not shapes: they are text with a hover background. Links in running text keep the underline and are the only underlined elements.

---

## 5. Screen by screen

For each screen: the content inventory in order of importance (what the user came for first), what is removed, shortened or moved, what becomes an icon, and for the ten key screens an ASCII wireframe of the phone's first viewport (390 × 844, drawn at 40 columns ≈ 26 lines) and of the desktop (1280 × 800, drawn at 100 columns). In the wireframes `[Text]` is a button, `(icon)` an IconButton, `⋯` the Menu, `▾` a menu button, `──` a hairline, `▸` a row chevron.

### 5.1 Home (screens 02 empty, 03 with a person)

Inventory: (1) what is due, across persons; (2) coming appointments; (3) the persons; (4) add a person; (5) settings.

- Removed: the "Due for a photo" heading with "Nothing is due right now." as a section. When nothing is due the section does not render; the title's meta line says "Nothing due". The "Persons" `h1` stays.
- Moved: "Add a person" → IconButton `user-plus` in the app bar (visible label on desktop); the add form opens in a sheet (one field, Create). Settings → IconButton `settings` in the app bar.
- Rows: due marks as rows (title = mark, meta = person · due since date, trailing Due chip); appointments as rows (date, meta person · n to photograph); persons as rows with the initial circle and role as meta.
- Empty: "No persons yet. A person is you, or someone you look after." and the bottom bar primary "Add a person".

```
Phone                                     Desktop
┌──────────────────────────────────────┐  ┌──────────┬─────────────────────────────────────────────────────────────────────────────────────────┐
│ (mark)                (👤+) (⚙)       │  │ ◦ neVus  │                                                              [ (👤+) Add a person ]      │
│                                      │  │          │                                                                                         │
│ Persons                              │  │ Persons  │  Persons                                                                                │
│ 2 marks due · 1 appointment          │  │ Settings │  2 marks due · 1 appointment                                                            │
│                                      │  │          │                                                                                         │
│ Due                                  │  │          │  Due                                                                                    │
│ ▣ Left forearm                 ⏱Due  │  │          │  ▣  Left forearm            Ana · due since 12 Sep                              ⏱ Due   │
│   Ana · due since 12 Sep             │  │          │  ──────────────────────────────────────────────────────────────────────────────────────  │
│ ───────────────────────────────────  │  │          │  ▣  Right shoulder          Luis · due today                                    ⏱ Due   │
│ ▣ Right shoulder               ⏱Due  │  │          │                                                                                         │
│   Luis · due today                   │  │          │  Coming appointments                                                                    │
│                                      │  │          │  Appointment on 14 Oct      Ana · 2 marks to photograph                              ▸  │
│ Coming appointments                  │  │          │                                                                                         │
│ Appointment on 14 Oct             ▸  │  │          │  Persons                                                                                │
│   Ana · 2 marks to photograph        │  │          │  (A)  Ana                   Owner                                                    ▸  │
│                                      │  │          │  ──────────────────────────────────────────────────────────────────────────────────────  │
│ Persons                              │  │          │  (L)  Luis                  Manager                                                  ▸  │
│ (A) Ana                     Owner ▸  │  │          │                                                                                         │
│ ───────────────────────────────────  │  │          │                                                                                         │
│ (L) Luis                  Manager ▸  │  │          │                                                                                         │
│                                      │  └──────────┴─────────────────────────────────────────────────────────────────────────────────────────┘
│                                      │
└──────────────────────────────────────┘
```

### 5.2 Person (screens 04 empty, 05 placing, 05b zoomed, 12 with a mark)

Inventory: (1) the body map with the markers; (2) the marks list; (3) add a mark; (4) the tools used once a season: appointments, sessions, reports, calendar link, profile.

- Removed: "Back" link; "Owner" next to the title (→ meta line "Owner · 3 marks · 1 due"); the `h2` "Body map"; the `h2` "Marks" on the phone (the rows under the map are evidently the marks; the desktop keeps it as the right pane's heading); the five disclosure cards and their hints; "Tap a zone to select it." in the resting state (shown only while placing).
- Moved: the five tools become five **rows** at the end of the page (phone) and rail items (desktop), each with icon, title and a one-line *status* (not a description): "Appointments · 14 Oct, 2 of 5 ready" / "none planned"; "Full-body sessions · in progress, 7 of 18" / "last 12 Jun"; "Reports · 2 made"; "Calendar · linked since 3 Mar" / "not linked"; "Profile · analysis off · 64 photos, 210 MB". Each opens its tool as a sub-page under `/persons/:id/{appointments|sessions|reports|calendar|profile}` (same components as today's disclosures, rendered as a page with the header pattern; on the desktop the body map pane stays on the left). When a tool is live (appointment ahead, session open) its row moves to the top of the tool list and its status is in ink, not ink-2.
- Primary: "Add a mark" in the bottom bar (phone) / app bar (desktop). While placing, the bottom bar becomes `[Cancel] [Tap the body…]` (the primary disabled-looking state is avoided by replacing the label with the instruction and no button: the bar shows the instruction text and a quiet Cancel). After the spot is tapped, the **New mark form opens in a sheet** (name, type, first noticed, check every; primary "Create the mark") rather than inline under the map.
- Icons: zoom controls `zoom-in`, `zoom-out`, `expand` as 40 px IconButtons over the map's top-right corner on `--color-surface` at 90 %; the view toggle (Front / Back / Head / Hands / Feet) is the segmented control under the app bar, text segments with an underline, full width on the phone.
- Map height on the phone: `calc(100dvh - 56px - 44px - 24px - 64px - 40px)`, so the whole silhouette, the status line and the bottom bar fit the first viewport. The marks list starts below the fold; the markers on the map are the first list.
- The marks list rows: thumbnail, title, meta "Right pectoral · last visit 5 Oct", trailing Due chip or "next 3 Jan".

```
Phone                                     Desktop
┌──────────────────────────────────────┐  ┌──────────┬─────────────────────────────────────────────────────────────────────────────────────────┐
│ (‹)                              ⋯   │  │ ◦ neVus  │ (‹)  Ana                                                              [ (+) Add a mark ] │
│                                      │  │          │                                                                                         │
│ Ana                                  │  │ Persons  │  Ana                                                                                    │
│ Owner · 3 marks · 1 due              │  │ Settings │  Owner · 3 marks · 1 due                                                                │
│                                      │  │ ──────── │                                                                                         │
│ Front  Back  Head  Hands  Feet       │  │ Ana      │  Front  Back  Head  Hands  Feet              Marks                                      │
│ ‾‾‾‾‾                                │  │  Body map│  ‾‾‾‾‾                                                                                  │
│            ┌────┐          (+)(−)(⤢) │  │  Appoint.│          ┌────┐           (+)(−)(⤢)         ▣  Chest mark          ⏱ Due                │
│            │    │                    │  │  Sessions│          │    │                              Right pectoral · last visit 5 Oct          │
│         ┌──┴────┴──┐                 │  │  Reports │       ┌──┴────┴──┐                          ──────────────────────────────────────────  │
│       ┌─┤  ●       ├─┐               │  │  Calendar│     ┌─┤  ●       ├─┐                        ▣  Left forearm        next 3 Jan           │
│       │ │          │ │               │  │  Profile │     │ │          │ │                          Left lower forearm · last visit 12 Jun    │
│       │ │    ◐     │ │               │  │          │     │ │    ◐     │ │                        ──────────────────────────────────────────  │
│       └─┤          ├─┘               │  │          │     └─┤          ├─┘                        ▣  Right shoulder      next 20 Nov          │
│         │    ││    │                 │  │          │       │    ││    │                            Right shoulder · no visits yet            │
│         │    ││    │                 │  │          │       │    ││    │                                                                      │
│         │    ││    │                 │  │          │       │    ││    │                          Appointments      14 Oct · 2 of 5 ready  ▸  │
│         └────┴┴────┘                 │  │          │       └────┴┴────┘                          Full-body sessions    last 12 Jun        ▸  │
│                                      │  │          │                                              Reports              2 made             ▸  │
│ ● tracked  ◐ due                     │  │          │  ● tracked  ◐ due                            Calendar             not linked         ▸  │
│                                      │  │          │                                              Profile              analysis off       ▸  │
├──────────────────────────────────────┤  │          │                                                                                         │
│ [         Add a mark               ] │  └──────────┴─────────────────────────────────────────────────────────────────────────────────────────┘
└──────────────────────────────────────┘
Placing: the bar reads "Tap the zone where the mark is" (ink-2) with [Cancel] quiet at its left; after the zone zooms,
"Tap the exact spot in Right pectoral"; after the spot, the New mark sheet opens over the map.
```

### 5.3 Mark (screens 06 empty, 08 with visits)

Inventory: (1) the visits, newest first, with their photographs; (2) the latest size and whether it changed; (3) new visit; (4) compare; (5) size over time; (6) seen in sessions; (7) details, snooze, reports, trash.

- Removed: "Back to the person" link; the neutral "In 90 days" pill; the facts "First noticed —" when empty and "Check every" (both live in the edit form; "every 3 months" joins the meta line); "Compare visits" as an underlined link; "Show as a table" / "Download as CSV" as buttons; the Reports disclosure card; the red trash button.
- Shortened: the facts strip to two pairs: **Latest size** "5.0 ± 0.2 mm" and **Since 5 Oct** "+0.0 ± 0.2 mm · no detectable change" (the second pair only when a change exists). Meta line: "Right pectoral · Front · Mole · next check 3 Jan · every 3 months". Snooze: when due, the meta ends with the Due chip and the Menu offers "Remind me later ▸ In a week / In a month"; when snoozed, the meta says "reminder snoozed until 19 Oct" and the menu offers "Remind me again".
- Icons: app bar `columns-2` Compare (only with ≥ 2 photographed visits); Menu: `pencil` Edit details (opens the edit form in a sheet), `bell-off` Remind me later, `file-text` Reports (sub-page `/lesions/:id/reports`), separator, `trash-2` Move the mark to the trash (danger, confirm). Section "Size over time": IconButtons `table` and `download` at its right; metric choice becomes a select ("Longest diameter ▾") instead of a four-segment control that wraps.
- Visit rows: date (title, tabular), thumbnails strip of 56 px up to four, meta "1 photo · itching · ⚠ quality note"; tapping opens the visit. The timeline rail of the brief is not drawn; the dates in a column already are the timeline.
- Primary: "New visit" (bottom bar / app bar). Empty state: "No visits yet. The first visit is the first photo of this mark." with the same primary.

```
Phone                                     Desktop
┌──────────────────────────────────────┐  ┌──────────┬─────────────────────────────────────────────────────────────────────────────────────────┐
│ (‹)                        (⫼)  ⋯    │  │ ◦ neVus  │ (‹) Ana                               [ (⫼) Compare visits ]  [ New visit ]      ⋯    │
│                                      │  │          │                                                                                         │
│ Chest mark                           │  │ Persons  │  Chest mark                                                                             │
│ Right pectoral · Front · Mole ·      │  │ Settings │  Right pectoral · Front · Mole · next check 3 Jan · every 3 months                       │
│ next check 3 Jan · every 3 months    │  │ ──────── │                                                                                         │
│                                      │  │ Ana      │  LATEST SIZE          SINCE 5 OCT                                                       │
│ LATEST SIZE      SINCE 5 OCT         │  │  Body map│  5.0 ± 0.2 mm         +0.0 ± 0.2 mm · no detectable change                             │
│ 5.0 ± 0.2 mm     +0.0 ± 0.2 mm       │  │  …       │                                                                                         │
│                  no detectable change│  │          │  Visits                                       Size over time         (▦) (⇩)            │
│                                      │  │          │  5 Oct 2026                                   Longest diameter ▾                        │
│ Visits                               │  │          │  ┌────┐┌────┐                                 ┌────────────────────────────────────┐    │
│ 5 Oct 2026                           │  │          │  │    ││    │                                 │ mm                                 │    │
│ ┌────┐┌────┐                         │  │          │  └────┘└────┘                                 │ 6 ─────────────────────────────── │    │
│ │    ││    │                         │  │          │  2 photos · itching · ⚠ quality note          │ 5 ──●━━━━━━━━━━━━━━━━━━━━━━●───── │    │
│ └────┘└────┘                         │  │          │  ─────────────────────────────────────────    │ 4 ─────────────────────────────── │    │
│ 2 photos · itching · ⚠ quality note  │  │          │  12 Jun 2026                                  │      Jun            Oct           │    │
│ ───────────────────────────────────  │  │          │  ┌────┐                                       └────────────────────────────────────┘    │
│ 12 Jun 2026                          │  │          │  │    │                                       The shaded band is the uncertainty.      │
│ ┌────┐                               │  │          │  └────┘                                                                                 │
│ │    │                               │  │          │  1 photo                                      Seen in full-body sessions               │
│ └────┘                               │  │          │                                               ▣ 12 Jun · Chest and shoulders        ▸   │
│ 1 photo                              │  │          │                                                                                         │
├──────────────────────────────────────┤  └──────────┴─────────────────────────────────────────────────────────────────────────────────────────┘
│ [          New visit               ] │
└──────────────────────────────────────┘
```

### 5.4 Visit (screen 07)

Inventory: (1) the photographs, large; (2) add a photo; (3) the measurement, or measuring; (4) what the person noticed; (5) the quality note; (6) trash.

- Title: `h1` is the date ("5 Oct 2026") with the meta line "6:00 PM · Chest mark · Ana"; the back label is "Back to Chest mark".
- Photo: edge to edge on the phone (no gutter, no radius), `max-height: 60dvh`, `object-fit: contain` on `--color-photo-frame`; a horizontal strip of 56 px thumbnails under it when there are several, plus an **add tile** (56 px, dashed border, `camera` icon, label "Add a photo") at the strip's end. The quality note is an overlay chip bottom-left of the photo (`triangle-alert` + "Overexposed"); tapping it opens a sheet with the full flags and the hint. The amber five-line box under the photo is gone.
- Adding a photo: one act, one control. The primary "Take a photo" (bottom bar) opens the camera directly with kind = Close-up. "More ways to add" lives in the **Add a photo sheet** (opened from the add tile or from the Menu): kind as four choice chips (Close-up · With reference card · Overview · Other), then three rows `camera` Take a photo / `video` Live camera / `image` Choose a file, then one line "The photo stays on this server; location and device data are removed." The "Kind" select and the three buttons leave the page.
- Measurements section: rows "5.0 ± 0.2 mm × 5.0 ± 0.2 mm" (title, tabular) with meta "card · compactness 0.99 · colour contrast ΔE 46" and a trailing `trash-2` IconButton; section header carries `ruler` "Measure" (IconButton with label on desktop) when a measurement exists. Empty: "No measurement yet." (the bottom bar then says "Measure").
- Notes section: four **choice chips** (Itching · Bleeding · Pain · Looks different to me) and a textarea with placeholder "What you noticed, in your own words." The helper sentence is removed. Saving: the bottom bar shows "Save" only while something changed (dirty); otherwise it shows the state's primary.
- Primary by state: no photo → "Take a photo"; photo, no measurement → "Measure"; dirty → "Save"; otherwise the bar is hidden on the phone (the page has no pending action) and the desktop app bar shows "Measure" as secondary.
- Menu: `camera` Add a photo…, `ruler` Measure on another photo (when > 1 photo), separator, `trash-2` Move the visit to the trash (danger, confirm).
- Experimental proposals stay as the dashed `--color-info` block above Measurements, unchanged in content, with the Experimental chip.

```
Phone                                     Desktop
┌──────────────────────────────────────┐  ┌──────────┬─────────────────────────────────────────────────────────────────────────────────────────┐
│ (‹)                              ⋯   │  │ ◦ neVus  │ (‹) Chest mark                                                 [ (⟋) Measure ]    ⋯    │
│                                      │  │          │                                                                                         │
│ 5 Oct 2026                           │  │ Persons  │  5 Oct 2026                                                                             │
│ 6:00 PM · Chest mark · Ana           │  │ Settings │  6:00 PM · Chest mark · Ana                                                             │
│┌────────────────────────────────────┐│  │ ──────── │ ┌─────────────────────────────────────┐   Measurements                       (⟋)        │
││                                    ││  │ Ana      │ │                                     │   5.0 ± 0.2 mm × 5.0 ± 0.2 mm          (🗑)      │
││                                    ││  │  …       │ │                                     │   card · compactness 0.99 · ΔE 46                │
││                                    ││  │          │ │            photograph               │                                                  │
││            photograph              ││  │          │ │                                     │   Notes                                          │
││                                    ││  │          │ │                                     │   (Itching) (Bleeding) (Pain) (Looks different)  │
││                                    ││  │          │ │                                     │   ┌──────────────────────────────────────────┐   │
││                                    ││  │          │ │  ⚠ Overexposed                      │   │ What you noticed, in your own words.     │   │
││ ⚠ Overexposed                      ││  │          │ └─────────────────────────────────────┘   │                                          │   │
│└────────────────────────────────────┘│  │          │ ┌────┐┌────┐┌ ─ ─┐                        └──────────────────────────────────────────┘   │
│ ┌────┐┌────┐┌ ─ ─ ┐                  │  │          │ │    ││    │  📷 │                                                                       │
│ │    ││    │  📷  │                  │  │          │ └────┘└────┘└ ─ ─┘                                                                       │
│ └────┘└────┘└ ─ ─ ┘                  │  │          │                                                                                         │
│                                      │  │          │                                                                                         │
│ Measurements                   (⟋)   │  │          │                                                                                         │
│ 5.0 ± 0.2 mm × 5.0 ± 0.2 mm   (🗑)   │  │          │                                                                                         │
│ card · compactness 0.99 · ΔE 46      │  │          │                                                                                         │
│                                      │  │          │                                                                                         │
│ Notes                                │  │          │                                                                                         │
│ (Itching) (Bleeding) (Pain)          │  └──────────┴─────────────────────────────────────────────────────────────────────────────────────────┘
├──────────────────────────────────────┤
│ [          Take a photo            ] │   ← becomes "Measure" once a photo exists, "Save" while notes changed
└──────────────────────────────────────┘
```

### 5.5 Measure (no sheet in the gallery; inferred from `MeasurePage.tsx`)

Inventory: (1) the photograph as a canvas with the handles; (2) the current step and its one question; (3) the live readout with ±; (4) save; (5) the alternatives (coin, known length, circle, outline again, change the scale).

- Canvas page (direction C inside B): the photo fills the viewport under the app bar (`height: calc(100dvh - 56px - sheet)`), zoom and pan as today; the app bar title is "Measure" with the stepper "1 Scale · 2 Mark" as its subtitle on the phone and in the panel header on the desktop.
- The step content lives in a **bottom sheet that is open by default** (phone) at about 40 % of the height, draggable to 20 % to see more photo, or in the **right panel** (desktop). Scale step: one status line ("Reference card found, tilted 3°" with `check` in `--color-success`, or the tilted note in attention, or "No reference card in this photo."), then the primary "Use the card" in the bottom bar when found; the alternatives "Use a coin" and "Use a known length" as two secondary buttons in the sheet (they are the primary when no card is found: "Use a coin" primary, "Known length" secondary). Coin sub-tool: a select of denominations and the primary "Use this coin"; line sub-tool: the length field and "Use this length", with `rotate-ccw` Start again as an IconButton.
- Mark step: the readout as a facts strip of three (Longest · Across · Area) at `--text-xl` tabular with ±; flags as one-line attention notices; the primary "Save the measurement" in the bottom bar; IconButtons in the sheet header: `circle` Adjust as a circle (when an outline exists), `rotate-ccw` Outline again, `scaling` Change the scale.
- Removed from the page: the two-line zoom/keyboard hint (→ `circle-help` IconButton in the app bar opening a help sheet; the keyboard text also goes into the canvas's `aria-describedby`). The disclaimer shortens to one line under the readout: "Size only: it says nothing about what the mark is."

```
Phone                                     Desktop
┌──────────────────────────────────────┐  ┌──────────┬─────────────────────────────────────────────────────────────────────────────────────────┐
│ (‹)  Measure · 1 Scale  2 Mark   (?) │  │ ◦ neVus  │ (‹) 5 Oct 2026   Measure                                 [ Save the measurement ]  (?)  │
│┌────────────────────────────────────┐│  │          │ ┌────────────────────────────────────────────┐  1 Scale · 2 Mark                        │
││                                    ││  │ Persons  │ │                                            │                                          │
││                                    ││  │ Settings │ │                                            │  Check the outline.                      │
││                                    ││  │ ──────── │ │                                            │  Switch to a circle to adjust by hand.   │
││                                    ││  │ Ana      │ │                 ╭────╮                     │                                          │
││              ╭────╮                ││  │  …       │ │                 │ ●  │◦                    │  LONGEST        ACROSS        AREA       │
││              │ ●  │◦               ││  │          │ │                 ╰────╯                     │  5.0 ± 0.2 mm   4.8 ± 0.2 mm  19.1 mm²   │
││              ╰────╯                ││  │          │ │                                            │                                          │
││                                    ││  │          │ │                                            │  Size only: it says nothing about what   │
││                                    ││  │          │ │                                            │  the mark is.                            │
││                                    ││  │          │ │                                            │                                          │
│└────────────────────────────────────┘│  │          │ │                                            │  (○) Adjust as a circle                  │
│┌──── ▬▬ ───────────────────────────┐ │  │          │ │                                            │  (↺) Outline again                       │
││ Check the outline.    (○)(↺)(⤢)   │ │  │          │ │                                            │  (⤢) Change the scale                    │
││                                   │ │  │          │ └────────────────────────────────────────────┘                                          │
││ LONGEST     ACROSS      AREA      │ │  │          │                                                                                         │
││ 5.0±0.2 mm  4.8±0.2 mm  19.1 mm²  │ │  │          │                                                                                         │
││                                   │ │  │          │                                                                                         │
││ Size only: it says nothing about  │ │  │          │                                                                                         │
││ what the mark is.                 │ │  └──────────┴─────────────────────────────────────────────────────────────────────────────────────────┘
│├───────────────────────────────────┤ │
││ [      Save the measurement     ] │ │
│└───────────────────────────────────┘ │
└──────────────────────────────────────┘
```

### 5.6 Compare (screens 09 side by side, 10 differences, 11 slider)

Inventory: (1) the two photographs, as large as the device allows; (2) which two (earlier, later); (3) the view (side by side, on top, slider, differences) and its slider; (4) how they were lined up; (5) the differences legend.

- Removed: "Back to the mark" link; the title "Compare: Chest mark" becomes `h1` "Compare" with meta "Chest mark · Ana"; the three-line zoom hint (→ `circle-help` in the app bar); the two full-width native selects.
- Pickers: one row of two **menu buttons** (`Earlier ▾ 12 Jun · card` and `Later ▾ 5 Oct · card`, secondary-button shape, 50 % each) that open a sheet listing the visits with 48 px thumbnails and the photo kind; the chosen one is marked with `check`. The alignment line ("Lined up with the reference card.") is the caption under the photos at `--text-sm` ink-2, not a status above them.
- Order on the phone: pickers → photographs → mode control → slider/legend → caption. The photographs start at y ≈ 180 px and take the width; side by side on a 390 px phone becomes **stacked** (two photos of 390 × ~260) because two 180 px photos cannot be read; the shared zoom still applies. On the desktop they are side by side.
- Mode control: the segmented control (text + underline, four segments) under the photos where the thumb is; disabled segments (when not aligned) show at 0.45 opacity with a tooltip "Needs lined-up photos" and the abstained note as the caption.
- Differences: the legend ramp with "Similar" and "Different" plus one line: "Shows where to look; it measures nothing." and a "Learn more" quiet button that opens the full note in a sheet.
- Slider / opacity: a range input the width of the photo, label above it as `--text-sm`.

```
Phone                                     Desktop
┌──────────────────────────────────────┐  ┌──────────┬─────────────────────────────────────────────────────────────────────────────────────────┐
│ (‹)                              (?) │  │ ◦ neVus  │ (‹) Chest mark                                                                     (?)  │
│                                      │  │          │                                                                                         │
│ Compare                              │  │ Persons  │  Compare                                                                                │
│ Chest mark · Ana                     │  │ Settings │  Chest mark · Ana                                                                       │
│ [Earlier ▾ 12 Jun ][Later ▾ 5 Oct  ] │  │ ──────── │  [ Earlier ▾ 12 Jun · card ]  [ Later ▾ 5 Oct · card ]     Side by side  On top  Slider  Differences │
│┌────────────────────────────────────┐│  │ Ana      │                                                            ‾‾‾‾‾‾‾‾‾‾‾‾                 │
││                                    ││  │  …       │  ┌───────────────────────────────┐ ┌───────────────────────────────┐                    │
││           earlier                  ││  │          │  │                               │ │                               │                    │
││                                    ││  │          │  │                               │ │                               │                    │
││ ─20 mm─                            ││  │          │  │            earlier            │ │             later             │                    │
│└────────────────────────────────────┘│  │          │  │                               │ │                               │                    │
│┌────────────────────────────────────┐│  │          │  │                               │ │                               │                    │
││                                    ││  │          │  │ ─20 mm─                       │ │ ─20 mm─                       │                    │
││            later                   ││  │          │  └───────────────────────────────┘ └───────────────────────────────┘                    │
││                                    ││  │          │  Earlier · 12 Jun · card           Later · 5 Oct · card                                  │
││ ─20 mm─                            ││  │          │  Lined up with the reference card in both photos.                                      │
│└────────────────────────────────────┘│  │          │                                                                                         │
│ Side by side  On top  Slider  Diff.  │  │          │                                                                                         │
│ ‾‾‾‾‾‾‾‾‾‾‾‾                         │  │          │                                                                                         │
│ Lined up with the reference card.    │  └──────────┴─────────────────────────────────────────────────────────────────────────────────────────┘
│                                      │
└──────────────────────────────────────┘
```

### 5.7 Session (screen 13)

Inventory: (1) the next region to photograph, with its pose; (2) take the photo / skip; (3) progress; (4) the regions already photographed (to open) and the ones to come; (5) finish, delete.

- Removed: "Back to the person" link; the how-to paragraph (→ one line "Same light and distance each time." plus `circle-help` opening the tips: helper for the back, phone timer); the experimental note as a paragraph (→ Experimental chip in the meta line with a tooltip); 36 buttons.
- Header: `h1` "Session · 5 Oct 2026"; meta "In progress · 7 of 18 regions · 1 skipped"; a 4 px progress bar (`--color-accent` on `--color-surface-2`) under the meta.
- **Current region** is the only card on the page: title (region name), the pose text (two lines max; the catalogue's pose strings already fit), the sensitive-region line when it applies, and nothing else; the bottom bar holds `[Skip]` quiet and `[Take the photo]` primary.
- **All regions** as rows in protocol order: leading 48 px thumbnail when photographed, a hollow circle (`circle`, ink-3) when pending, a dashed circle (`circle-dashed`) when skipped; title = region; meta = "3 marks" / "not yet" / "skipped"; trailing `chevron-right` on photographed rows (→ zone page). Tapping a pending or skipped row makes it the current region (the card above updates; the skipped row's status becomes "photographing after all"). No button in any row.
- Menu: `check` Finish the session, separator, `trash-2` Delete the session (danger; the existing confirm text becomes the dialog's sentence).
- Desktop: rows on the left (the list is the pane), the current region's card with its pose and the primary on the right; the photographed region's photo preview appears in the right pane when its row is selected, with "Open" and "Take it again".

```
Phone                                     Desktop
┌──────────────────────────────────────┐  ┌──────────┬─────────────────────────────────────────────────────────────────────────────────────────┐
│ (‹)                           (?) ⋯  │  │ ◦ neVus  │ (‹) Ana                                                     [ Take the photo ]  (?)  ⋯  │
│                                      │  │          │                                                                                         │
│ Session · 5 Oct 2026                 │  │ Persons  │  Session · 5 Oct 2026                                                                   │
│ In progress · 7 of 18 · 1 skipped    │  │ Settings │  In progress · 7 of 18 regions · 1 skipped                                              │
│ ━━━━━━━━━━━━━━━━━━━━━━━━░░░░░░░░░░░░ │  │ ──────── │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│                                      │  │ Ana      │                                                                                         │
│ ┌──────────────────────────────────┐ │  │  …       │  ● Face                     3 marks  ▸     ┌──────────────────────────────────────────┐ │
│ │ Next: Upper back                 │ │  │          │  ● Scalp                    skipped        │ Next: Upper back                         │ │
│ │ Stand with your back to the      │ │  │          │  ● Chest and shoulders      2 marks  ▸     │ Stand with your back to the camera, arms │ │
│ │ camera, arms relaxed. Frame from │ │  │          │  ● Abdomen and pelvis       1 mark   ▸     │ relaxed. Frame from the neck to the      │ │
│ │ the neck to the bottom of the    │ │  │          │  ○ Upper back               next           │ bottom of the shoulder blades.           │ │
│ │ shoulder blades.                 │ │  │          │  ○ Lower back and buttocks  not yet        │                                          │ │
│ └──────────────────────────────────┘ │  │          │  ○ Right arm, front         not yet        │ Someone can help with the back, or prop  │ │
│                                      │  │          │  ○ Left arm, front          not yet        │ the phone up and use its timer.          │ │
│ ● Face                    3 marks ▸  │  │          │  ○ Right arm, back          not yet        │                                          │ │
│ ───────────────────────────────────  │  │          │  ○ Left arm, back           not yet        │                            [ Skip ]      │ │
│ ◌ Scalp                   skipped    │  │          │  ○ Palms                    not yet        └──────────────────────────────────────────┘ │
│ ───────────────────────────────────  │  │          │  ○ Backs of the hands       not yet                                                     │
│ ● Chest and shoulders     2 marks ▸  │  │          │  ○ Right leg, front         not yet                                                     │
│ ───────────────────────────────────  │  │          │  …                                                                                      │
│ ● Abdomen and pelvis       1 mark ▸  │  └──────────┴─────────────────────────────────────────────────────────────────────────────────────────┘
│ ───────────────────────────────────  │
│ ○ Upper back                 next    │
├──────────────────────────────────────┤
│ [Skip]      [     Take the photo   ] │
└──────────────────────────────────────┘
```

### 5.8 Session zone (screens 14 tapped, 15 with marks, 15b blurring)

Inventory: (1) the photograph with its numbered marks; (2) the marks on it and what each is (linked, proposed, unlinked); (3) record or link a tapped mark; (4) blur a part; (5) take it again.

- Removed: "Back to the session" link; the two-line hint as a paragraph (→ one line at `--text-sm` under the `h1`: "Tap a mark on the photo to record it."); the mark panel as an inline card with two selects and three buttons.
- Canvas: the photo edge to edge on the phone, `max-height: 55dvh`; numbered dots as today (pending proposals dashed).
- Marks list: rows with the 48 px crop, title (the mark's name or "Proposed: …" / "Not linked to a mark"), meta ("found again" / "no clear spot found"), selected row with `--color-accent-2` background. Tapping a row or a dot opens the **mark sheet** (phone) / **right panel** (desktop).
- Mark sheet for a tapped spot ("The mark you tapped"): a radio list of the marks the region covers (sorted as today, with their thumbnails) and a last item "A new mark…" that reveals the zone select and the optional name; one primary that reads "Link to it" or "Record a new mark" according to the choice; quiet Cancel. For an existing mark the same sheet opens with the current link selected and a Menu (`trash-2` Remove from this photo). For a proposal: title "Proposed spot", the crop, "Yes, it is that mark" primary and "Not a mark" secondary.
- Menu (app bar): `eye-off` Blur a part of the photo, `camera` Take the photo again, separator, nothing destructive here (the photo's deletion is the session's).
- Blur mode: the hint line becomes "Tap two opposite corners of the area to blur."; a **toolbar sheet** at the bottom with `undo-2` Remove the last area (IconButton), quiet Cancel and the primary "Blur 2 areas"; one line under: "Replaces the photo for good; the marks stay." with a Learn more.

```
Phone                                     Desktop
┌──────────────────────────────────────┐  ┌──────────┬─────────────────────────────────────────────────────────────────────────────────────────┐
│ (‹)                              ⋯   │  │ ◦ neVus  │ (‹) Session · 5 Oct                                                                 ⋯  │
│                                      │  │          │                                                                                         │
│ Chest and shoulders                  │  │ Persons  │  Chest and shoulders                                                                    │
│ Tap a mark on the photo to record it.│  │ Settings │  Tap a mark on the photo to record it.                                                  │
│┌────────────────────────────────────┐│  │ ──────── │ ┌────────────────────────────────────────────┐  Marks on this photo                     │
││                                    ││  │ Ana      │ │                                            │  ▣  1. Chest mark                        │
││      ①                             ││  │  …       │ │       ①                                    │     found again                          │
││                                    ││  │          │ │                                            │  ──────────────────────────────────────  │
││              ●                     ││  │          │ │                   ●                        │  ▣  2. Proposed: a spot not linked       │
││                                    ││  │          │ │                                            │     to any mark                          │
││                       ②            ││  │          │ │                            ②               │                                          │
││                                    ││  │          │ │                                            │  ┌──────────────────────────────────┐    │
││                                    ││  │          │ │                                            │  │ Proposed spot                    │    │
│└────────────────────────────────────┘│  │          │ │                                            │  │ ┌────┐                           │    │
│                                      │  │          │ │                                            │  │ │crop│  Looks like: Chest mark   │    │
│ ▣ 1. Chest mark                      │  │          │ └────────────────────────────────────────────┘  │ └────┘                           │    │
│   found again                        │  │          │                                                 │ [ Yes, it is that mark ]         │    │
│ ───────────────────────────────────  │  │          │                                                 │ [ Not a mark ]                   │    │
│ ▣ 2. Proposed: a spot not linked     │  │          │                                                 └──────────────────────────────────┘    │
│   to any mark                        │  │          │                                                                                         │
│                                      │  │          │                                                                                         │
│                                      │  └──────────┴─────────────────────────────────────────────────────────────────────────────────────────┘
│                                      │
└──────────────────────────────────────┘
Tapping a row or a dot opens the mark sheet from the bottom (radio list of marks the region covers, "A new mark…", one primary).
```

### 5.9 Sessions compare (screen 16)

Same page pattern as 5.6: `h1` "Two sessions", meta "12 Jun and 5 Oct"; the region picker as one menu button (`Region ▾ Chest and shoulders`) full width; photographs next; the mode control under them; the alignment status as the caption; the zoom hint removed. Rows of the regions both sessions share could replace the select on the desktop (left pane); on the phone the menu button is enough.

### 5.10 Settings (screens 17 plain, 18 sudo dialog, 19 second factor, 20 recovery codes)

Inventory, as the person who opens Settings needs it: (1) appearance (language, theme, ±) because it is changed first and most; (2) account and sign out; (3) reminders and notifications; (4) second factor; (5) reference card; (6) your data and the trash; (7) administration; (8) about.

- The fourteen cards become **a list of rows**, in groups separated by a group label (`--text-xs` 600 ink-3, uppercase not used; sentence case): *Account* (Account · jose, administrator ▸; Appearance's three rows inline: Language ▾, Theme ▾, Show uncertainty switch; Sign out as a row), *Reminders* (Reminders · "daily email off" ▸; Notifications on this device · "this device off" ▸), *Security* (Second factor · "on, 10 codes left" ▸), *Measuring* (Reference card · "print verified 49.6 mm" ▸), *Your data* (Export and trash · "2 exports" ▸), *Administration* (Accounts ▸, Email delivery · "not set up" ▸, Webhooks · "2" ▸, Backups · "last night" ▸, Instance ▸), and the About line at the end as meta text ("neVus 1.2.0 · a documentation aid, not a diagnostic tool").
- Each row opens a **sub-page** at `/settings/{section}` with the header pattern; the sub-page holds exactly what the card held today, with its intro reduced to one line under the title and the rest behind "Learn more". On the desktop the rail lists the sections (as today's left list) and the right pane shows the one chosen — one at a time, never the whole stack. `/settings` on the desktop opens Appearance.
- Removed: "(administrator)" from titles (the group label says it); the row of pills on the phone; the "Sections" sticky list; every "Save" button next to a single field (fields save on change with a short "Saved" status, as the appearance selects already do); the push and reminders intros (→ one line + Learn more).
- Second factor sub-page: status line, then one primary ("Set up a second factor" / when on: Menu with `refresh-cw` New recovery codes and `shield-off` Turn it off). Setup: the three steps as a numbered list, the QR at 176 px, the secret as a `copy` row, the code field, primary "Turn the second factor on", quiet Cancel. Recovery codes: the ten codes as a two-column tabular block, `download` Save as a file (secondary with label), primary "I have saved them".
- Sudo dialog: unchanged in content; the Confirm button is a normal primary (never drawn disabled before typing); the dialog is a sheet on the phone.

```
Phone                                     Desktop
┌──────────────────────────────────────┐  ┌──────────┬─────────────────────────────────────────────────────────────────────────────────────────┐
│ (‹)                                  │  │ ◦ neVus  │                                                                                         │
│                                      │  │          │                                                                                         │
│ Settings                             │  │ Persons  │  Second factor                                                                          │
│                                      │  │ Settings │  A code from your phone, besides the password.                                          │
│ Account                              │  │ ──────── │                                                                                         │
│ (👤) jose                          ▸ │  │ Account  │  The second factor is on · 10 recovery codes left.                      ⋯               │
│      administrator                   │  │ Appear.  │                                                                                         │
│ ───────────────────────────────────  │  │ Reminders│  Recovery codes                                                                         │
│ Language                   English ▾ │  │ Notific. │  Each signs you in once if the phone is lost. They are not shown again.                 │
│ ───────────────────────────────────  │  │ ▌2nd fac.│                                                                                         │
│ Theme             Follow the device ▾│  │ Ref. card│  ns934-zymyv     arfvr-8fqfq                                                            │
│ ───────────────────────────────────  │  │ Your data│  tp9h4-fc96v     ey9mx-9g7cb                                                            │
│ Show measurement uncertainty    (●─) │  │ ──────── │  xee82-qwjgj     uzqbv-j4xnn                                                            │
│ ───────────────────────────────────  │  │ Accounts │  vrgxd-zps9t     f8zme-kg9sy                                                            │
│ (⇥) Sign out                         │  │ Email    │  amvf7-8rbhb     xbs66-frjcd                                                            │
│                                      │  │ Webhooks │                                                                                         │
│ Reminders                            │  │ Backups  │  [ (⇩) Save as a file ]   [ I have saved them ]                                         │
│ (🔔) Reminders      daily email off▸ │  │ Instance │                                                                                         │
│ ───────────────────────────────────  │  │ ──────── │                                                                                         │
│ (📱) Notifications   this device off▸│  │ About    │                                                                                         │
│                                      │  │          │                                                                                         │
│ Security                             │  │          │                                                                                         │
│ (🛡) Second factor   on · 10 codes ▸ │  └──────────┴─────────────────────────────────────────────────────────────────────────────────────────┘
│                                      │
└──────────────────────────────────────┘
```

### 5.11 Evaluation set (screen 21) and trash (screen 22)

- Evaluation: `h1` "Evaluation set", meta "2 to label · 14 labelled"; the three-line intro → one line ("Outline your own photos to measure the analyzers; labels stay on this server.") with Learn more; "How the outline analyzer does" as a section with the table or "No photo is labelled yet."; the CLI note as a `code` chip row with `copy` ("nevus evaluate"); the filter as the segmented control; the photo grid of 160 px tiles with caption rows (person · mark, date) stays — it is the one place where a grid of equal tiles is right.
- Trash: `h1` "Trash", meta "Kept for 30 days"; the intro sentence removed (the meta says it); rows per item (kind icon `person-standing` / `circle-dot` / `camera` / `image`, title, meta "removed for good on 4 Nov"), trailing `rotate-ccw` Restore (IconButton with label on desktop) and a Menu with `trash-2` Delete now (danger). Empty: "The trash is empty."

### 5.12 Sign-in (screens 01 claim, 23 password, 24 code, 25 recovery code)

Inventory: (1) the two fields and the button; (2) the brand; (3) the alternatives (recovery code, authenticator, back); (4) the tagline.

- Brand block: dark paper, 72 px tall on the phone and the desktop, the wordmark 120 px wide (the shell no longer carries it, so this is where it is seen; it does not need to be large to be seen).
- Form: `max-width: 22rem`, centred horizontally, placed at the top third (`margin-top: 10dvh`), not vertically centred (it drifts on tall screens); `h1` "Sign in" at `--text-2xl`; fields; the primary **enabled** from the start, full width; errors inline under the field.
- Claim: the intro shortened to one line ("The first account is the administrator; it creates the others.").
- Second factor: `h1` "One more step", one line of instruction, the field with `inputmode="numeric"` and `autocomplete="one-time-code"`, primary "Continue"; the alternatives as two quiet buttons in one row under the form ("Use a recovery code" · "Back").
- Tagline at the bottom at `--text-sm` ink-3, centred, as today.

```
Phone                                     Desktop
┌──────────────────────────────────────┐  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│██████████████████████████████████████│  │██████████████████████████████████████  neVus  ██████████████████████████████████████████████████████│
│███████████  neVus  ██████████████████│  │                                                                                                      │
│██████████████████████████████████████│  │                                                                                                      │
│                                      │  │                                                                                                      │
│                                      │  │                              Sign in                                                                 │
│   Sign in                            │  │                                                                                                      │
│                                      │  │                              Username                                                                │
│   Username                           │  │                              ┌────────────────────────────────────────┐                              │
│   ┌──────────────────────────────┐   │  │                              │                                        │                              │
│   │                              │   │  │                              └────────────────────────────────────────┘                              │
│   └──────────────────────────────┘   │  │                              Password                                                                │
│   Password                           │  │                              ┌────────────────────────────────────────┐                              │
│   ┌──────────────────────────────┐   │  │                              │                                        │                              │
│   │                              │   │  │                              └────────────────────────────────────────┘                              │
│   └──────────────────────────────┘   │  │                              [              Sign in                 ]                              │
│   [          Sign in            ]    │  │                                                                                                      │
│                                      │  │                                                                                                      │
│                                      │  │                                                                                                      │
│                                      │  │                                                                                                      │
│                                      │  │                                                                                                      │
│                                      │  │                                                                                                      │
│                                      │  │                                                                                                      │
│  Because 'I think it was smaller'    │  │                        Because 'I think it was smaller' is not data.                                 │
│  is not data.                        │  └─────────────────────────────────────────────────────────────────────────────────────────────────────┘
└──────────────────────────────────────┘
```

### 5.13 Pages without a sheet in the gallery

- **Appointment** (`AppointmentPage.tsx`): header pattern (`h1` "Appointment on 14 Oct", meta "In 8 days · 2 of 5 ready"); the checklist as rows (mark, meta "never photographed" / "due 12 Oct", trailing `camera` IconButton "Photograph now", with its label on the desktop); photographed items as rows with `check` in success; the report block as a row "Report for the appointment · not made" ▸ opening the options sheet; Menu: `pencil` Change the date or the note, separator, `trash-2` Delete the appointment.
- **Tool sub-pages of the person** (appointments, sessions list, reports, calendar, profile): the header pattern, the one-line intro, the list as rows, the form in a sheet from the primary ("Prepare an appointment", "Start a session", "Make a report", "Make a calendar link"); profile: the experimental switch row with its one-line hint, the usage line, "Export this person" as a row ▸ (sheet with the passphrase fields), and "Delete this person for good" only in the Menu (danger, the type-the-name confirmation inside the dialog).

---

## 6. Copy rules

1. **Helper text is one line.** At `--text-sm` on a 390 px phone a line holds about 48 characters; a helper may be at most two lines, so **≤ 90 characters** including the full stop. Anything longer is cut or moved.
2. **Where long explanations go**, in this order of preference: (a) nowhere — if the control's label already says it, the explanation is deleted; (b) a **placeholder** inside the field; (c) a **one-line hint + "Learn more"** (quiet button) that opens a **help sheet** (phone) or **dialog** (desktop) carrying the full current text; (d) the **`circle-help` IconButton** in the app bar for page-level help (zoom and keyboard hints, session tips). Tooltips are only for icon-only controls' labels, never for explanations.
3. **Intros under titles are status, not description.** A sub-page's first line says what is true now ("The second factor is on · 10 recovery codes left."), not what the feature is.
4. **No sentence starts with the product's name** inside the interface except the About line. "neVus records it and never interprets it" is a README sentence.
5. **Empty states**: one sentence that starts with "No … yet." and ends with what to do, ≤ 90 characters; the action is the page's primary, not a second button.
6. **Buttons**: a verb phrase, ≤ 3 words, no article when a noun follows a verb ("Add a mark" keeps the article because "Add mark" is not how the catalogue speaks; "Measure", "Compare visits", "New visit" are fine). Menu items may be longer ("Move the mark to the trash") because they are read, not scanned.
7. **Status and meta** use " · " as the separator, dates absolute ("12 Sep 2026") with a relative word only where it changes a decision ("due since 12 Sep", "in 8 days").
8. **The forbidden words** of `PRODUCT_REQUIREMENTS.md` §7 stay forbidden; "quality note" replaces "quality warnings" everywhere a person sees it (the flags themselves keep their wording).
9. **Confirmation dialogs**: title = the verb with a question mark; one sentence of consequence; buttons = the verb and Cancel.
10. **Accessible labels** of icon-only controls are the catalogue's current full strings (so `images.takePhoto` "Take a photo" labels the `camera` tile, `compare.open` "Compare visits" labels the `columns-2` button); no new strings are needed for them.

### Ten rewrites from the English catalogue

| Key | Today | Proposed | Where it goes |
| --- | --- | --- | --- |
| `sessions.howTo` | "Use the same light and distance each time. Someone can help with the back, or prop the phone up and use its timer." (119) | "Same light and distance each time." (35) | One line under the session meta; the rest in the `circle-help` sheet "Tips for a session" |
| `compare.zoomHint` | "Pinch or use the mouse wheel to zoom, drag to move; side by side, both photos follow. With a keyboard: + and − zoom, the arrows move." (134) | removed from the page | `circle-help` sheet; the keyboard sentence becomes the canvases' `aria-describedby` |
| `images.privacyNote` | "The photo stays on this server. Everything the camera embedded except the capture time and orientation is removed before it is stored." (138) | "Stays on this server; location and device data are removed." (61) | One line at the foot of the Add-a-photo sheet |
| `observations.notesHint` | "What you noticed, in your own words. neVus records it and never interprets it." (81) | "What you noticed, in your own words." (36) | Placeholder of the Notes textarea |
| `quality.title` + `quality.hint` | "Saved with quality warnings" / "The visit is kept as it is. If you can, take the photo again." | chip "Overexposed"; sheet title "Quality note"; sheet last line "Kept as it is. Retake if you can." (33) | Photo overlay chip → sheet |
| `observations.emptyText` | "A visit is one dated look at the mark: photos, your notes and what you noticed." (80) | "No visits yet. The first visit is the first photo of this mark." (64) | Empty state sentence; primary "New visit" in the bar |
| `push.intro` | "When marks are due for a photo, this device gets one notification a day, after the reminder hour. The message travels encrypted through your browser's push service, which sees only that something was sent." (205) | "One notification a day when a mark is due." (43) + Learn more | Settings → Notifications sub-page; full text in the Learn more sheet |
| `evaluation.intro` | "Label your own photos to see how the analyzers do on them: draw the mark's true outline and say whether the photo is good. The labels stay on this server." (155) | "Outline your own photos to measure the analyzers; labels stay here." (67) + Learn more | Under the `h1` |
| `auth.claimIntro` | "Nobody has an account yet. The first account becomes the administrator and creates the others; there is no open registration." (126) | "The first account is the administrator; it creates the others." (62) | Under the `h1` on the claim page |
| `sessions.blurNote` | "The blurred photo takes this one's place. The original is removed at once, not kept in the trash, and cannot be brought back; the marks on the photo stay." (154) | "Replaces the photo for good; the marks stay." (45) + Learn more | Under the blur toolbar; full text in the Learn more sheet and in the confirmation dialog |

Two more that are labels rather than helpers: `lesions.dueIn` "In {{count}} days" as a pill becomes meta text "next check {{date}}" (the date says more than a count); `settings.showUncertainty` "Show measurement uncertainty (±)" stays as the switch label — it is the one case where the ± in the label is the clearest word.

---

## 7. Implementation order

From most to least valuable; the first six change the impression of every screen before any page is touched. Sizes: S = under half a day, M = one to two days, L = three days or more.

1. **App bar replaces the brand block and the back links** — `Shell.tsx`, `Shell.module.css`, a new `AppBar` component (back IconButton, title that appears on scroll, two action slots, Menu slot); every page's `<p><Link>Back…</Link></p>` and `<h1>` move into the header pattern (§4.2). The dark block stays only in `AuthLayout`. **M.**
2. **Rows instead of cards** — a `Row` component (leading image / initial / icon, title, meta, trailing); `LesionList`, `HomePage` persons, `DueList`, `UpcomingAppointments`, `SessionsSection`, `Reports` list, `ExportList`, `UsersAdmin`, `WebhookSettings`, `TrashPage`, `Sightings`, zone marks list; the `Card` border/shadow removed from list items; hairlines between rows. **M.**
3. **Bottom action bar and the action policy** — a `ActionBar` component (sticky bottom on phone, slot in the AppBar on desktop; one primary, optional quiet); every page's primary moves into it; secondary buttons move into the AppBar's IconButtons or the Menu per §4.3; destructive buttons move into the Menu with a `ConfirmDialog` (new, S) — `LesionPage`, `ObservationPage`, `SessionPage`, `ZonePage`, `AppointmentPage`, `PersonPage`, `MeasurePage`. **L.**
4. **Type, spacing and chips** — `base.css` and the module CSS: the header pattern sizes, section spacing, the chip variants (Due filled; Removed/Resolved outline; Experimental outline; quality as icon + meta), removal of the neutral "In n days" pill, tabular facts strip. **S.**
5. **Control shapes down to five** — `Segmented` restyled as text + underline (no filled teal segment, no wrapping into two rows: on the phone use a select when more than four options); `Button` heights and radii unified; `Switch` added; choice chips added (`Chip`); native selects and textareas styled as the field shape; the CSS-border chevron replaced by Lucide `chevron-down`/`chevron-right`. **M.**
6. **Copy pass** — the ten rewrites of §6 and the removal of intros where the rule says so; a `HelpSheet` component for "Learn more" and the `circle-help` IconButton; `en.json` (and the other locales) updated; the lint list unchanged. **S.**
7. **Person page** — map height formula, view toggle as the segmented control, zoom IconButtons over the map, status line only while placing, New mark form in a `Sheet` (new component, used by 8–12 too), the five tools as rows → sub-pages under `/persons/:id/*` (routes in `App.tsx`; the existing section components render inside a page wrapper); desktop rail context block. **L.**
8. **Visit page** — edge-to-edge photo with the quality overlay chip → sheet, thumbnails strip with the add tile, the Add-a-photo sheet (kind chips + three sources + one privacy line), measurements as rows with `trash-2`, notes as choice chips + placeholder, state-dependent primary. `PhotoGallery.tsx`, `QualityNotice.tsx`, `VisitMeasurements.tsx`, `ObservationPage.tsx`. **L.**
9. **Mark page** — facts strip of two, meta line, Compare as AppBar IconButton, Menu (edit in a sheet, snooze, reports sub-page, trash), visit rows with thumbnail strips, chart section header IconButtons, metric select. `LesionPage.tsx`, `SizeChart.tsx`, `SnoozeControls.tsx`. **M.**
10. **Session page** — current-region card + bottom bar, all regions as rows that select, Menu for finish/delete, progress bar, desktop two panes with the selected region on the right. `SessionPage.tsx`. **M.**
11. **Settings** — rows in groups at `/settings`, sub-pages at `/settings/:section` (routes), desktop master–detail with the rail, fields saving on change with a "Saved" status, second factor and recovery codes per §5.10, sudo as a sheet on the phone. `SettingsPage.tsx`, `Group.tsx` (becomes the sub-page wrapper), `ReminderSettings`, `PushSettings`, `SecondFactorSettings`, `ReferenceCardSettings`, `AdminSettings`, `UsersAdmin`, `WebhookSettings`, `BackupSettings`. **L.**
12. **Compare and sessions compare** — picker menu buttons with a visit sheet, photographs first, stacked on the phone, mode control under the photos, caption line, legend line + Learn more. `ComparePage.tsx`, `ComparisonViewer.tsx`, `SessionComparePage.tsx`. **M.**
13. **Zone page and blur** — canvas height, marks rows, mark sheet with the radio list, proposal sheet, blur toolbar sheet, Menu. `ZonePage.tsx`. **M.**
14. **Measure page** — default-open bottom sheet / right panel, stepper in the AppBar, readout strip, IconButtons for the alternatives, help sheet, one-line disclaimer. `MeasurePage.tsx`. **M.**
15. **Sign-in and claim** — 72 px brand block, 22 rem form at the top third, enabled primary, one-line claim intro, alternatives in one row. `AuthLayout.tsx`, `CredentialsForm.tsx`, `SecondFactorForm.tsx`, `ClaimPage.tsx`. **S.**
16. **Home** — meta line instead of the empty Due section, `user-plus` and `settings` IconButtons, add-person sheet, initial circles. `HomePage.tsx`. **S.**
17. **Evaluation, trash, appointment** — header pattern, rows, Menu, code chip. **S.**
18. **Gallery and review** — `pnpm run shots` regenerated; the rubric of §8 applied to the new sheets; `DESIGN_REVIEW.md` gets a third-pass section pointing here. **S.**

Items 1–6 are the first third and touch every screen; after them the gallery already reads as one quiet application even before any page's own layout changes.

---

## 8. Evaluation rubric

Ten criteria, 0 to 3 each (30 in total), to apply to a screenshot sheet of each screen on the phone and on the desktop. A screen passes at 24 or more with no criterion at 0. The notes say what a 3 looks like; a 0 is the current gallery's state for most screens.

| # | Criterion | 3 looks like |
| --- | --- | --- |
| 1 | **First viewport is content** | On the phone, content (a photograph, the body map, the first rows) begins within 140 px of the top; no brand block, no back link line, no section heading before the first content; the primary action is visible without scrolling. |
| 2 | **One primary action** | Exactly one filled accent button on the screen (bottom bar on the phone, app bar on the desktop), its label a verb phrase of ≤ 3 words, and it matches the page's state. |
| 3 | **Buttons on the page** | Apart from the primary, at most two icon buttons in the app bar, one "more" menu, and section-header icon buttons; no row contains a button; no secondary button appears in the content column except inside a sheet or a form. |
| 4 | **Boxes** | No card around a list or a list item; hairlines and spacing separate rows and sections; cards only on sheets, dialogs, the session's current region and the experimental proposal. |
| 5 | **The photograph (or the map) is the hero** | On canvas pages it fills the width (edge to edge on the phone) and at least 50 % of the first viewport's height; nothing coloured overlays it except the quality chip and the tool's own handles. |
| 6 | **Explanations** | No paragraph of more than two lines in the content column; helpers ≤ 90 characters; long text reachable only through "Learn more" or the help icon; no sentence starts with "neVus". |
| 7 | **Hierarchy and type** | Three visible levels (title / section or row title / meta) using the roles of §4.8; facts in tabular figures; no "—" for an empty fact; dates absolute. |
| 8 | **Icon versus text** | Every icon-only control is universal and in an expected position, has an accessible label (and a visible one on the desktop where §4.3 marks V); every domain action is text; status chips carry words. |
| 9 | **Control shapes and states** | Only the five shapes of §4.12 are present; the segmented control has no filled segment; no control is drawn disabled as its resting state; focus rings visible in the keyboard pass; hover backgrounds on rows. |
| 10 | **Calm** | No red outside system errors and the confirmation dialog; attention only as the Due chip and the quality icon; destructive actions only inside the menu behind a confirmation; nothing reads as a verdict. |

How to apply: score the phone sheet and the desktop sheet separately for each of the 27 screens, note the lowest criterion per screen, and fix in the order of §7 the pattern that scores lowest across the most screens. The accessibility sweep (zero findings) stays a precondition, not a criterion.
