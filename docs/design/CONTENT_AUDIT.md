# Content audit: what is on each screen, and why

- Status: audit of the interface at 1.2.0 (branch `feature/design-pass-3`, gallery of 2026-10-05), made from the 798 strings in `frontend/src/lib/i18n/locales/en.json`, the 27 phone and 27 desktop sheets in `frontend/.screenshots/sheets/`, and the page components. It audits what is on each page and why it is there; it does not propose colours or type.
- Independence: it was written apart from the design pass running in parallel and contradicts [`DESIGN_REVIEW.md`](DESIGN_REVIEW.md) where the two disagree (listed below).
- The brief, in the Product Owner's words: no buttons cluttering the page; information well organised; icons or text depending on what is optimal in each case.

What this audit contradicts in the earlier review:

1. Folding the person page's tools under titled cards was half the distance: a folded card still costs a title, a two-line hint and a chevron, five times. For once-a-season tools the optimal form is a labelled icon chip, and live state (an appointment ahead, a session in progress) is content, not a tool, so it gets a card of its own.
2. The settings page's row of section pills on the phone adds a scrolling row to a scrolling page. Once the administrator groups are one fold, the members' settings fit in little more than one viewport and the pills go. The desktop side list stays.
3. The session page's "next region leads" still leaves two buttons under each of the other seventeen regions: 52 targets on one phone page. One region at a time is the only structure that fits the task.
4. The deferred question of a bottom bar is answered by the task analysis: no bar. The home page already is the "due" page; what it lacks is a camera on each due row.

What it agrees with and keeps: one primary action per screen, chosen by the page's state; destructive actions apart; the photograph first on the visit page; two panes from 900 px; the brand framing the entrance; the calm register.

## How things were counted

- A **target** is anything a finger can tap that is not the content itself: buttons, links used as actions, fields, selects (1 each), each option of a segmented control, each disclosure header, each checkbox. Not counted: the shell's three constant targets (wordmark, Persons, Settings) and content rows (a person, a mark, a visit, a photo, a region, a map zone or marker), which are what the page is for.
- Counts are for the **phone sheet, whole page, in the state photographed**. Desktop differs only where said. The tablet (820 px) sits below the 900 px breakpoint and behaves as a tall phone; the phone verdicts apply to it.
- **Need** is how often a real user needs the element: *every use* (each time they photograph a mark), *weekly*, *season* (a few times a year), *once* (set-up or recovery).
- **Height** is the phone page's length in viewports: the sheet header's device pixels divided by 2 202, the height of a page that does not scroll.

### Summary

| Sheet | Screen | Targets now | Targets proposed | Height now |
|---|---|---|---|---|
| 01 | Claim | 4 | 4 | 1.0 |
| 02 | Home, empty | 1 | 1 | 1.0 |
| 03 | Home | 1 | 1 (+1 per due mark) | 1.0 |
| 04 | Person, empty | 14 | 13 | 1.9 |
| 05 | Person, placing | 14 | 13 | 2.0 |
| 05b | Person, zoomed | 15 | 14 | 2.0 |
| 06 | Mark, empty | 5 | 3 | 1.0 |
| 07 | Visit | 14 | 12 | 2.2 |
| 08 | Mark | 17 | 10 | 2.3 |
| 09 | Compare, side by side | 7 | 7 | 1.6 |
| 10 | Compare, differences | 7 | 7 | 1.4 |
| 11 | Compare, slider | 8 | 8 | 1.3 |
| 12 | Person | 14 | 13 | 1.9 |
| 13 | Session | 52 | 4 | 4.4 |
| 14 | Session zone, tapped | 7 | 5 | 1.3 |
| 15 | Session zone, mark selected | 10 | 5 | 1.7 |
| 15b | Session zone, blur | 4 | 4 | 1.2 |
| 16 | Sessions compare | 2 (6 once aligned) | 2 (6) | 1.4 |
| 17 | Settings | 29 | 13 | 3.1 |
| 18 | Settings, password dialog | 3 in the dialog | 3 | 3.3 |
| 19 | Settings, second-factor set-up | 32 | 16 | 4.0 |
| 20 | Settings, recovery codes | 33 | 17 | 3.8 |
| 21 | Evaluation set | 4 | 4 | 1.0 |
| 22 | Trash | 1 (+2 per item) | 1 (+2 per item) | 1.0 |
| 23 | Sign in | 3 | 3 | 1.0 |
| 24 | Sign in, code | 4 | 4 | 1.0 |
| 25 | Sign in, recovery code | 4 | 4 | 1.0 |
| | **Total over the 27 sheets** | **309** | **191** | |

The settings page is photographed four times (17 to 20), which weights it in the total. Three screens carry most of the excess: the session page (52 targets, 4.4 viewports), the settings page (29 to 33 targets, 3 to 4 viewports) and the mark page (17 targets). The person page's count barely moves (14 to 13), but its five tool cards, about 50 words, become one row of three chips and a menu.

## 1. Inventory by screen

### 1.1 Entrance: 01 Claim, 23 Sign in, 24 Code, 25 Recovery code

Four sheets, one pattern: the wordmark on dark paper, a centred form, the tagline below. The register is right and the count is minimal; the findings are copy.

| Element | Job | Need | Verdict |
|---|---|---|---|
| Wordmark | Says where you are | every use | keep |
| H1 "Claim this instance" | Names the first-run step | once | keep |
| Intro "Nobody has an account yet. The first account becomes the administrator…" (125 chars) | Explains closed registration | once | shorten: "This first account becomes the administrator." |
| Username, Password, Repeat the password | Credentials | once | keep |
| Hint "At least 10 characters. A sentence works well." | Password rule | once | keep |
| "Create the administrator" | Submit | once | keep as text (consent-like, once) |
| H1 "Sign in", Username, Password, "Sign in" | Credentials | every use | keep |
| H1 "One more step" | Second factor | every use when on | keep |
| Intro "Enter the six-digit code from the authenticator app on your phone." / "Enter one of the recovery codes you saved… Each works once." (104) | Says which code | every use | shorten to one line each: "The six-digit code from your authenticator app." / "A recovery code you saved. Each works once." |
| Code or Recovery code field, "Continue" | Input | every use | keep |
| "Use a recovery code instead" / "Use the authenticator instead" | Switch | once | keep as quiet text (ambiguous as an icon) |
| "Back" | Back to the password | once | keep as quiet text; on sheet 25 it wraps to its own line on the phone, so put both links in one row |
| Tagline footer | Brand | — | keep |
| SSO variant: title, "This neVus signs people in through your single sign-on…", "I have signed in" | Proxy mode | every use on SSO installs | keep; shorten the text to "Sign in with your single sign-on, then return here." |

Phone targets: 4 / 3 / 4 / 4, unchanged.

### 1.2 Home: 02 empty, 03 with a person

| Element | Job | Need | Verdict |
|---|---|---|---|
| H1 "Persons" | Title | every use | keep (nav label and title agree) |
| "Add a person" (secondary, in the header) | Create a profile | once per person | move: a quiet row with a leading `UserPlus` at the end of the persons list; the header holds nothing |
| H2 "Due for a photo" and the list | The household's to-do | every use | keep; it is the home's reason to exist |
| Due row: mark name · person · "due today" / "due since {date}" | Identify what is due | every use | keep; add the action: a `Camera` icon button "Photograph now" that creates the visit and opens the camera (the appointment page already does exactly this with `useStartVisit`) |
| "Nothing is due right now." | Empty state | every use | keep, one line |
| H2 "Coming appointments" and cards | Live appointments | season | keep (shown only when one exists) |
| Empty state "No persons yet" + "A person is somebody whose skin marks you keep a record of: you, or someone you look after." + button | First run | once | keep; shorten the text to "You, or someone you look after." |
| Add-person form (Name, Create, Cancel) | Create | once | keep inline |
| Person card: name · role | Open the hub | every use | keep; add "N due" at the right when marks are due, so the card and the due list agree |

Phone targets: 1 → 1 (+1 per due mark). The home is already the right page for "check what is due"; it lacks only the shortest path from a due row to the camera.

### 1.3 Person: 04 empty, 05 placing, 05b zoomed, 12 with a mark

| Element | Job | Need | Verdict |
|---|---|---|---|
| "Back" link | Up to home | every use | iconify `ArrowLeft`, accessible name "Back to Persons"; desktop shows "Persons". It is the only page whose back link says just "Back" |
| H1 name, "Owner" at the right | Identify | every use | keep the name; show the role only when the viewer is not the owner (that is when it changes what they can do) |
| H2 "Body map" | Section title | every use | remove on the phone (the map is self-evident; keep it as the section's accessible name); on desktop it is already inline with the toggle |
| View toggle Front / Back / Head / Hands / Feet | Which silhouette | every use | keep as text (five short words; the detail views have no unambiguous icons) |
| Zoom + / − / reset | Zoom | weekly | keep: the map pinches already, but the buttons are the keyboard and mouse route; swap the glyphs for `ZoomIn`, `ZoomOut`, `Maximize` |
| Markers and zones | The content | every use | keep; tapping a zone should start placing (next rows) |
| Status line "Tap a zone to select it." | Hint | every use | replace: selecting a zone does nothing except show its name, so make the zone tap the first step of placing and say "Tap where the mark is." |
| "Add a mark" (primary) | Start placing | weekly | keep as text with a leading `Plus`; the one primary button; also reached by tapping the map. Today it sits just below the fold on a 390 × 844 phone; removing the "Body map" heading and the five cards brings it up |
| Placing hints "Tap the zone where the mark is: the map zooms in on it. Then tap the exact spot." (84) / "Tap the exact spot of the mark in Right pectoral." | Guide | weekly | shorten: "Tap the zone, then the exact spot." / "Tap the exact spot in Right pectoral." |
| Placing "Cancel" (quiet) | Abort | weekly | iconify `X` in the map's corner on the phone (where the zoom reset sits); desktop text "Cancel" |
| New-mark form: Name (+ hint), "Suggest a name", Type, First noticed, Check every, "Create the mark", "Cancel" | Describe | weekly | keep; "Create the mark" stays text; rename "Check every" to "Photo every" |
| H2 "Marks" and rows (thumbnail, name, zone · view · last visit, due badge) | The content | every use | keep; the row already says what matters |
| Empty "No marks yet" + "Add a mark by tapping its place on the body map." | First run | once | keep |
| Disclosure "Appointments" + hint (two lines) | Tool | season | move: an icon chip `CalendarPlus` "Appointment" in a tool row under the marks; its form opens as a sheet. When an appointment is ahead, a live card ("Appointment on 12 Nov · 2 marks to photograph") appears above the marks and links to the appointment page |
| Disclosure "Full-body sessions" + hint | Tool | season | move: chip `PersonStanding` "Session" that starts a session or resumes the open one; past sessions and "Compare the last two sessions" live on a sessions page one tap further; a live card when one is in progress |
| Disclosure "Calendar" + hint | Tool | once | fold: an item "Calendar link" in the page's ⋯ menu, opening a sheet |
| Disclosure "Reports" + hint | Tool | season | move: chip `FileText` "Reports" opening a sheet |
| Disclosure "Profile settings" + hint | Tool | once | fold: ⋯ item "Profile settings" opening its own page (experimental analysis, storage, export, delete for good) |
| The five hints (about 50 words) | Explain each tool | — | remove; the chips' labels suffice, and each sheet carries its own one line |

Phone targets: 14 → 13 (Back, five views, two zoom, Add a mark, three chips, ⋯); 05b: 15 → 14. The count moves little; the reading does: five cards become one row, and the first viewport gains the room that puts "Add a mark" above the fold.

### 1.4 Mark: 06 empty, 08 with visits

| Element | Job | Need | Verdict |
|---|---|---|---|
| "Back to the person" | Up | every use | iconify `ArrowLeft`, name "Back to Ana"; desktop "Ana" |
| H1 mark name + due badge ("In 90 days") | Identify, state | every use | keep |
| "Right pectoral · Front · Mole" | Where, what | every use | keep |
| Facts: First noticed, Check every, Latest size, Since {date} (change · "no detectable change"), Next check | The record | every use | keep; hide a fact with no value (today "First noticed —", "Latest size —"); rename "Check every" → "Photo every", "Next check" → "Next photo" |
| Snooze "Not now: In a week / In a month" (when due) / "Reminder snoozed until {date} · Remind me again" | Defer | weekly when due | fold: `BellOff` icon button "Not now" with the two items in a menu; the snoozed state stays one line with "Remind me again" as quiet text |
| Notes paragraph | Record | weekly | keep |
| "New visit" (primary) | The main action | every use | keep as text with a leading `Camera`; the only primary |
| "Edit details" (secondary) | Edit | season | iconify `Pencil` "Edit details", desktop label yes |
| Offline form "Keep this visit" | Capture offline | rare | keep (appears only when offline) |
| H2 "Visits" + link "Compare visits" | Section, tool | every use / weekly | keep the heading; iconify `Columns2` "Compare visits" on the heading's right, desktop label yes |
| Visit rows: date, "N photos", thumbnails, chip "Quality warnings", symptom chips, notes | Timeline | every use | keep; the "Quality warnings" chip becomes the amber dot the visit page already uses on the thumbnail; symptom chips stay |
| Empty "No visits yet" + "A visit is one dated look at the mark: photos, your notes and what you noticed." | First run | once | keep |
| H2 "Size over time" + "At each visit. The shaded band is the measurement uncertainty." | Trend | weekly | keep the heading; shorten the subtitle to "Shaded: measurement uncertainty." |
| Metric segmented (Longest diameter / Area / Compactness / Colour contrast) | Choose the series | weekly | keep as text (no unambiguous icons); it already hides metrics with fewer than two values |
| Chart | Trend | weekly | keep |
| "Show as a table" (secondary) | Alternate view | season | iconify `Table` ↔ `ChartLine`, desktop label yes |
| "Download as CSV" (link) | Export | once | iconify `Download` with the label "CSV" on desktop |
| Note under the table on compactness and ΔE (234) | Explain | once | move to a help sheet behind `CircleHelp` beside the table |
| "Seen in full-body sessions" (crops) | Cross-reference | season | keep (appears only when any) |
| Disclosure "Reports" + hint + intro + Language + Paper + "Make the record of this mark" + list ("Download the PDF (3 pages, 86.3 kB)", "Delete") | PDF | season | fold: ⋯ item "PDF record" opening a sheet with one "Make the record" button; Language and Paper default from Settings behind "Options"; made records list with a `Download` icon and their delete in a row menu |
| "Move the mark to the trash" (danger, after a hairline) | Destroy | once | fold: last item of the ⋯ menu, as text, separated by a hairline; the trash (30 days) is the undo |

Phone targets: 06: 5 → 3 (Back, New visit, ⋯). 08: 17 → 10 (Back, New visit, Compare, four metrics, Table, CSV, ⋯); 11 when a made record shows its download.

### 1.5 Visit: 07

| Element | Job | Need | Verdict |
|---|---|---|---|
| "Back to Chest mark" | Up | every use | iconify `ArrowLeft`, name "Back to Chest mark" |
| H1 "October 5, 2026 at 6:00 PM" | Identify | every use | keep the date, but add the mark's name: once the back link is an icon, the page no longer says which mark this is. Title "Chest mark", subtitle the date and time |
| H2 "Photos" | Section | every use | remove on the phone (the photo is the first thing under the title); keep as the section's accessible name |
| Hero photo, thumbnails, the "!" dot | The hero | every use | keep |
| Quality notice: "Saved with quality warnings", the flag lines, "The visit is kept as it is. If you can, take the photo again." | Caption | every use when flagged | keep the flag lines (the useful part); shorten the footer to "Kept as it is. Retake if you can." |
| "Kind" select (Close-up / With reference card / Overview / Other) | Role of the next photo | every use | move to the photo's preview dialog, per photo, after capture; default inferred (card found → With reference card, else Close-up). It removes a decision the user must make before shooting, and it fixes a model error: the kind belongs to each photo, not to the next upload |
| "Take a photo" (system camera) | Capture | every use | merge with "Live camera": one `Camera` button "Take a photo" that opens the live camera when the device has one (it carries the "last time" ghost) and the system camera otherwise. Primary with text while there is no photo; an icon in the gallery's toolbar once there is one |
| "Live camera" (secondary) | Capture with ghost | every use | merge (above) |
| "Choose a file" (secondary) | Import | season | iconify `ImagePlus` "Add from files", desktop label yes |
| "Last time: try to match the distance and the angle." + thumbnail | Guidance | every use | keep (the most useful line on the page); shorten to "Last time: match distance and angle." |
| "The photo stays on this server. Everything the camera embedded except the capture time and orientation is removed before it is stored." (134) | Reassure | once | remove from the page: the upload toast (`images.uploaded`) already says it; the full sentence goes to Settings → About |
| Proposals section (experimental) | Review proposals | weekly when on | keep the structure; shorten the intro (section 4) |
| H2 "Measurements" + row "5.0 ± 0.2 mm × 5.0 ± 0.2 mm · card · compactness 0.99 · colour contrast ΔE 46" + "Delete" | Data | every use | keep the heading and the size; demote compactness and contrast to a quieter second line; iconify the row's "Delete" as `X` "Delete this measurement" |
| "Measure on the photo" / "Measure on photo N" (a link styled as a primary button) | The second main action | every use | keep as text with a leading `Ruler`, "Measure"; make it a button, not a link borrowing the button's look |
| "No measurements for this visit yet." / "Add a photo to measure the mark." | Empty | every use | keep, one line |
| H2 "Your notes" + "What you noticed, in your own words. neVus records it and never interprets it." (86) | Section | every use | keep the heading; shorten the hint to "In your own words." (the boundary sentence lives in About) |
| Four symptom checkboxes | Data | every use | keep (they are the record); as toggle chips they take one row instead of four |
| Notes textarea | Data | every use | keep |
| "Save" (primary when changed) | Persist | every use | keep |
| "Move visit to trash" (danger) | Destroy | once | fold: ⋯ menu in the title row, text item |

Phone targets 14 → 12 (Back, Camera, Files, Measure, measurement ×, four symptoms, notes, Save, ⋯). The order the review set (photo first) is right; the clutter is the toolbar under it: a select, three buttons and a paragraph become two icons.

### 1.6 Compare: 09, 10, 11, and 16 Sessions compare

| Element | Job | Need | Verdict |
|---|---|---|---|
| "Back to the mark" / "Back to the session" | Up | weekly | iconify `ArrowLeft` with the parent's name |
| H1 "Compare: Chest mark" / "Two sessions, region by region" + dates | Identify | weekly | keep; align the two: "Compare: Chest mark" / "Compare: sessions of 5 Oct and 12 Nov" |
| Earlier / Later selects (date · kind) | Choose the photos | weekly | keep (long lists want a select); they already default to first and last |
| Region select (16) | Choose the region | season | keep |
| Alignment line "Lined up with the reference card in both photos." / "Lined up using 759 points…" / abstained notice | Method | weekly | keep, one line; the abstained notice may stay two sentences because it explains a missing control |
| Mode segmented (Side by side / On top / Slider / Differences) | View | weekly | keep as text (the four have no unambiguous icons) |
| "Pinch or use the mouse wheel to zoom, drag to move; side by side, both photos follow. With a keyboard: + and − zoom, the arrows move." (133) | Teach | once | remove from the flow: nothing on touch (pinch and drag are the convention); the keyboard half appears as a caption only while the canvas has keyboard focus |
| Canvases, scale bar, captions | The content | weekly | keep |
| Opacity / split sliders | Control the view | weekly | keep (one at a time) |
| Difference legend: ramp, "Similar / Different", note (146) | Explain | weekly | keep the ramp; shorten the note to "Colour differences only; it measures nothing." |

Phone targets 7 / 7 / 8 / 2 (6), unchanged; the gain is three lines of text on each screen.

### 1.7 Session: 13

The worst screen by the brief's measure: eighteen regions, each a card with a title, a "How to pose" disclosure, a status line and two buttons; 52 targets and 4.4 viewports on a phone; the one primary button the same size as the fifteen secondary ones below it.

| Element | Job | Need | Verdict |
|---|---|---|---|
| "Back to the person" | Up | season | iconify `ArrowLeft` "Back to Ana" |
| H1 "Session of October 5, 2026" + "In progress · 1 of 18 regions photographed" | Identify, progress | season | keep; the progress as a count in the title row ("1 / 18") |
| "Use the same light and distance each time. Someone can help with the back, or prop the phone up and use its timer." (118) | Tips | once | move into the first region's card, shown once per session; shorten to "Same light and distance each time. Use the timer for the back." |
| Experimental note (173) | Explain proposals | once | shorten to one line (section 4), shown once |
| Per region: H2 name | Identify | season | keep, but only the **current** region is a card; the other seventeen are rows of a compact progress list (name, status dot, thumbnail when captured) that tap to jump |
| Per region: pose text (current) / "How to pose" disclosure (others) | Guide | season | keep inline for the current region only; a region shows its pose when it becomes current |
| Per region: "This region may include intimate areas. Skip it if you prefer; nothing else depends on it." | Consent | season | keep, for the current region when it applies |
| Per region: status "Not photographed yet / Skipped / N marks / Looking for spots on the photo…" | State | season | keep as the row's status (a dot and a word or a count) |
| Per region: thumbnail link | Open the zone page | season | keep in the row |
| Per region: "Take the photo" / "Take it again" | Capture | season | one only: on the current card, primary; "Take it again" lives on the zone page as `Camera` "Take the photo again" with a desktop label |
| Per region: "Skip" / "Photograph it after all" | Skip | season | "Skip" as quiet text on the current card only; "Photograph it after all" as the action of a skipped region's row when opened |
| "Finish the session" (primary) | Close | season | keep as text; it becomes the current card's action once no region is pending, otherwise it sits in ⋯ |
| "Delete the session" (quiet) + `window.confirm` | Destroy | once | fold: ⋯ item, text; the app's dialog instead of `window.confirm` |

Phone targets 52 → 4 (Back, Take the photo, Skip, ⋯) plus eighteen content rows that fit one viewport; the page falls from 4.4 viewports to about 1.3.

### 1.8 Session zone: 14 tapped, 15 mark selected, 15b blur

| Element | Job | Need | Verdict |
|---|---|---|---|
| "Back to the session" | Up | season | iconify `ArrowLeft` "Back to the session" |
| H1 region name | Identify | season | keep |
| "Tap the photo where a mark is, then link it to a mark you already follow or record it as a new one." (103) / "The marks seen on this photo." | Guide | season | shorten: "Tap a mark on the photo to link or record it." |
| Photo canvas with numbered dots | The content | season | keep |
| "Blur a part of the photo" (quiet) | Privacy tool | once | iconify `EyeOff` "Blur part of the photo" in the photo's corner toolbar, desktop label yes |
| Blur panel: title, note (154), "Blur N areas", "Remove the last area", "Cancel" | Tool | once | keep; shorten the note (section 4); `Undo2` for "Remove the last area" with a desktop label; the apply button stays text (irreversible) |
| Panel "The mark you tapped": "A mark you follow" select + "Link to it"; "Or record a new mark in" zone select + "Name (optional)" + "Record a new mark"; "Cancel" | Link or create | season | keep as two steps: the select and "Link to it" first; "Record a new mark instead" as a disclosure that reveals zone, name and button |
| H2 "Marks on this photo" + rows (crop, "1. Chest mark") | List | season | keep |
| Panel "Mark" / "Proposed spot · Experimental": crop, link to the mark, the whole link chooser again, "Remove from this photo" / "Not a mark" / "Yes, it is that mark" | Edit a mark | season | keep the crop and the link; fold the chooser behind "Change the link…" (today it shows in full for a mark that is already linked, the common case); the actions stay text |

Phone targets: 14: 7 → 5; 15: 10 → 5; 15b: 4 → 4.

### 1.9 Settings: 17, 18 password dialog, 19 second-factor set-up, 20 recovery codes

| Element | Job | Need | Verdict |
|---|---|---|---|
| H1 "Settings" | Title | season | keep |
| Section pills × 12 on the phone (horizontal scroll) / side list on desktop | Jump | season | remove on the phone (with the folds below, the page is about 1.2 viewports: scrolling beats a scrolling row of pills); keep the desktop list, cut to 7 entries (8 for administrators) |
| Account: "jose · administrator", "Sign out" | Identity, exit | season | keep; "Sign out" as text with a leading `LogOut` |
| Appearance: Language, Theme, "Show measurement uncertainty (±)" | Preferences | once | keep; shorten the label to "Show uncertainty (±)" |
| Reminders card: intro (146), Email address + "Save", "Send me a daily email when marks are due", "Add an email address to turn email reminders on." | Email channel | once | merge with the notifications card into one "Reminders" card of channel rows: *Home page* (always on, no control), *Email* (address field and switch), *This device* (switch); the intro goes |
| "Notifications on this device (experimental)": intro (205), two status lines, "Turn on for this device", "Send a test notification", iPhone note (98) | Push channel | once | merge (above); "Send a test" becomes quiet text under the row; the iPhone note shows only on iOS |
| Disclosure "Second factor" + hint | Security | once | keep folded; name the group "Security" (so a password change can join it later); when open, the intro (139) repeats the hint: remove it |
| Set-up: steps 1–3, QR, "Or type:" secret, "Code the app shows now", "Turn the second factor on", "Cancel" | Set-up | once | keep; the three steps become one line: "Scan with your authenticator app, then enter its code." |
| On: "The second factor is on. 10 recovery codes left.", "New recovery codes", "Turn it off" | State | once | keep as text (both are consequential) |
| Recovery codes: title, intro (118), list, "Save as a file", "I have saved them" | One-time display | once | keep; `Download` for "Save as a file" with a desktop label; "I have saved them" stays text (acknowledgement) |
| Disclosure "Reference card" + hint; intro (122), two download links, "Measured length of the 50 mm line" + hint + "Save", verified / unverified line | Calibration | once | keep folded; remove the intro (the hint covers it); the two downloads stay text ("A4", "US Letter") |
| Disclosure "Your data" + hint; intro (97), export list, "Export the whole instance (administrator)", "Open the trash" | Data | once | keep folded; remove the intro; "Open the trash" as a row with a leading `Trash2` |
| Disclosures "Accounts (administrator)", "Email delivery (administrator)", "Webhooks", "Backups (administrator)", "Instance (administrator)" | Operate | once | fold: one "Administration" group, visible to administrators only, holding the five; drop the suffixes (Webhooks is admin-only too and lacks one) |
| Accounts rows: name, description, "Enable / Disable", "Set a new password", "Turn the second factor off" | Operate | once | fold the three row actions into a ⋯ menu per row (text items) |
| Email delivery form (seven fields, "Save", test address, "Send a test") | Operate | once | keep (a form is a form); remove the intro (113), keep the hint |
| Webhooks: intro (205), rows (name · kind, address, last sent, "On", "Send a test", "Delete"), form (Kind, Name, Address, Secret, "Add the webhook") | Operate | once | shorten the intro to the hint; per row, `Send` for the test and the delete in a ⋯ |
| Backups: intro (197), status, verification notice, "Back up now", "Read the latest backup back now" | Operate | once | shorten the intro; the buttons stay text |
| Instance: "Language for new accounts", link "Evaluation set: label your photos to measure the analyzers" | Operate | once | keep; shorten the link to "Evaluation set" |
| About: intended-use statement, version | Legal | — | keep, unfolded, last: it is where the statement is reachable in the app and it must stay |
| Password dialog (18): "Confirm it is you", "This action needs your password again.", Password, "Confirm", "Cancel" | Re-authenticate | once | keep as is |

Phone targets: 17: 29 → 13; 19: 32 → 16; 20: 33 → 17.

### 1.10 Evaluation set: 21 (administrator tool)

| Element | Job | Need | Verdict |
|---|---|---|---|
| "Back to the settings" | Up | once | iconify `ArrowLeft` "Back to Settings" (and fix the article: the trash page says "Back to settings") |
| H1 + intro (154) | Explain | once | shorten the intro: "Outline your photos' marks to measure the analyzers." |
| H2 "How the outline analyzer does" + table / "No photo is labelled yet." | Results | once | keep |
| Quality sentence (167) | Results | once | move into the table as rows (poor photos warned about, good photos flagged, agreement) |
| "These figures use the proposals already made. To run the current analyzer afresh…" (121) | Operator note | once | shorten: "Figures use existing proposals. To rerun: nevus evaluate." |
| H2 "Photos" + filter (To label / Labelled / All) + grid | Work list | once | keep |
| Label page (not in the gallery): intro (133), tool segmented, canvas, legend, "Start from the proposal", "Remove the last point", "Clear the outline", quality radios, "Save the label", "Remove the label" | Labelling | once | keep; `Undo2` and `RotateCcw` for the two outline actions with desktop labels; the rest text |

Phone targets 4 → 4.

### 1.11 Trash: 22

| Element | Job | Need | Verdict |
|---|---|---|---|
| "Back to settings" | Up | once | iconify `ArrowLeft` "Back to Settings" |
| H1 + "Deleted marks, visits and photos stay here for 30 days, then go for good." (76) | Explain | once | keep (short, and it is the rule) |
| Empty state, two lines | Empty | once | keep |
| Item rows: label, kind · person · "removed for good on {date}", "Restore", "Delete now" (danger) | Recover | once | "Restore" stays the row's text button; "Delete now" moves into a per-row ⋯ (the red buttons leave the list; the count per row stays 2) |

Phone targets 1 (+2 per item), unchanged in count; no red button in view.

### 1.12 Not in the gallery, inventoried from the code

**Measure** (`features/measure/MeasurePage.tsx`). Back "Back to the visit"; H1 "Measure"; steps "Scale / The mark"; the canvas; the zoom hint (127); one step panel. Scale step: searching / found / tilted / not-found notice; "Use the reference card" (when found), "Use a coin", "Use a known length"; coin tool (prompt, denomination select, tilt note of 108 chars, "Use this coin"); line tool (prompt, length field, "Use this length", "Start again"). Mark step: "Tap the mark." / "Check the outline. Switch to a circle to adjust it by hand."; results (Longest, Across, Area); flag notices; "Save the measurement", "Adjust as a circle", "Outline again", "Change the scale"; "A measurement describes size. It says nothing about what the mark is." (73).

Verdicts: when the card is found and within the tilt limit, **start at the mark step**. The page already selects the card reference in an effect, yet the user must press "Use the reference card" to move on; skipping that press saves a tap on every measured visit. "Change the scale" (quiet text) brings the scale step back. The three scale options keep their text with leading `CreditCard`, `Coins`, `Ruler`. "Adjust as a circle" → `Circle` with a desktop label; "Outline again" → `RotateCcw` with a desktop label; "Save the measurement" stays text (primary). The zoom hint becomes a keyboard-focus caption as on compare. The size sentence is a language-rule statement and stays. Phone targets: scale step 4, mark step 5 → the mark step's 5, with the scale step skipped for card photos.

**Appointment** (`features/appointments/AppointmentPage.tsx`). Back "Back to Ana"; H1 "Appointment on {date}" + "In 12 days"; the note; "Change the date or the note" (secondary), "Delete the appointment" (quiet); H2 "To photograph before the appointment" + "2 of 5 ready" + rows with a primary "Photograph now" each, or "Every mark on the list has a new photo."; H3 "Photographed for the appointment" + rows with a tick; H2 "Report for the appointment" + intro (104) + Language + Paper + "Make the report" / "Make it again" + the download link.

Verdicts: edit and delete into ⋯ (text items); "Photograph now" → a `Camera` icon button per row with a desktop label (a column of primary buttons is the pattern the review removed from the session page); the report intro goes (the heading says it); Language and Paper behind "Options" with defaults from Settings; "Make the report" stays text. Targets 7 + N → 4 + N.

**Live camera** (`features/capture/LiveCamera.tsx`): preview, "Last photo" ghost toggle, "Torch", the shutter (already an icon), "Close". Keep; `Flashlight` for the torch and `X` for close, text on desktop for the ghost toggle.

**Photo preview dialog** (`features/images/PhotoGallery.tsx`): image, date · size, "Move to trash" (danger), "Close". Add the per-photo "Kind" select here; `X` for close; the trash action stays text.

**Offline quick visit** (`features/capture/QuickVisit.tsx`): notice (128), Kind, "Take a photo", "N photos ready", Notes, "Keep this visit". Keep; shorten the notice to "Offline. Photos are kept here and upload later."

## 2. Tasks, in order of frequency, and the shortest path to each

Taps are counted from the home page after sign-in. Typing, the system camera and scrolling are not taps; a scroll is noted where the target sits below the fold on a 390 × 844 phone.

| # | Task | Need | Path now | Taps now | Path proposed | Taps proposed |
|---|---|---|---|---|---|---|
| 1 | Photograph a mark that is due | every use | Due row → mark page → "New visit" → "Take a photo" → camera; then "Measure on the photo" → "Use the reference card" → tap the mark → "Save the measurement" | 3 to the camera; 7 with a measurement | The due row's `Camera` → camera (the visit is created on the way, as the appointment page does today); then "Measure" → tap the mark → "Save" (the scale step is skipped when the card is found) | 1 to the camera; 4 with a measurement |
| 2 | Add a new mark | weekly | Person → scroll past the map → "Add a mark" → tap the zone → tap the spot → "Create the mark" | 5 and a scroll | Person → tap the zone (placing starts) → tap the spot → "Create the mark"; "Add a mark" stays for those who look for a button | 4, no scroll |
| 3 | Look at how a mark changed | weekly | Person → mark (facts: latest size, change since) → "Compare visits" → a mode | 2 to the facts and chart; 3 to compare; 4 to a mode | Same route; the facts stay in the first viewport and Compare is an icon on the Visits heading | 2 / 3 / 4 (unchanged) |
| 4 | Prepare a dermatology visit and take the report | season | Person → open "Appointments" → date → "Prepare the appointment" → N × "Photograph now" → "Make the report" → "Download the PDF" | 5 + N; afterwards the appointment card on Home is 1 tap | Person → "Appointment" chip (sheet) → date → "Add" → N × `Camera` → "Make the report" → `Download` | 5 + N (same count; a shorter page, and a live card on the person page) |
| 5 | Run a full-body session | season | Person → open "Full-body sessions" → "Start a session" → 18 × "Take the photo" (and skips) → "Finish the session" | 22 | Person → "Session" chip (starts or resumes) → 18 × "Take the photo" → "Finish" | 21, on a page with 4 targets instead of 52 |
| 6 | Check what is due across the household | every use | Home | 0 | Home (unchanged); each person card also says "N due" | 0 |
| 7 | Change a setting | season | Settings → a pill or a scroll → the control | 2–3 | Settings → the control (members' groups within one viewport once the administrator groups are one fold) | 2; 3 for administrator groups |
| 8 | Sign in | every use | Sign-in page → "Sign in" (→ code → "Continue") | 1 (2 with a second factor) | unchanged | 1 (2) |

Across the eight tasks: 46 + N taps now, 36 + N proposed. The one that matters is the first: the most frequent task goes from three taps to one, and a measured visit from seven to four.

## 3. The navigation model

```
Home: due marks [Camera] · coming appointments · persons (N due) · Settings
 ├─ due row ──Camera──► new Visit ──► Measure
 ├─ appointment card ──► Appointment (checklist · report)
 ├─ person ──► Person hub: map · marks · [Appointment] [Session] [Reports] ⋯
 │    ├─ mark ──► Mark: facts · New visit · visits · chart ──► Visit ──► Measure
 │    │                                                     └──► Compare
 │    ├─ Appointment ──► sheet ──► Appointment page
 │    ├─ Session ──► Session (one region at a time) ──► Zone ──► Sessions compare
 │    ├─ Reports ──► sheet
 │    └─ ⋯  Calendar link · Profile settings (experimental analysis, storage, export, delete for good)
 └─ Settings: account · appearance · reminders · security · reference card · your data · administration · about
      └─ Trash · Evaluation set
```

Why:

1. **The home page is the due list.** Task 6 is already zero taps, and task 1 becomes one tap when the due row carries the camera. No separate "Due" page and no bottom bar: the home page is that page. This answers the question the review deferred: keep the top bar. A bottom bar's three destinations (Persons, Due, Settings) are two destinations here, and the brief's "Add" and "Visit" entries are properties of a person and of a mark, not of the app.
2. **The person page is the hub, and the map is its control.** Tapping the map adds a mark; the list opens one; the tools are one row. Everything used once a season is one tap away but outside the reading order; everything used once (calendar link, profile, delete) is two taps away behind ⋯.
3. **Live state surfaces; tools do not.** An appointment ahead or a session in progress is content and gets a card in the hub; the tool that created it stays a chip. This replaces the disclosure that "opens by itself", which put a form into the reading order.
4. **One primary action per page, chosen by state** (as the review said): Home none (its rows carry the actions); Person "Add a mark"; Mark "New visit"; Visit "Take a photo" → "Measure" → "Save"; Measure "Save the measurement"; Session "Take the photo" → "Finish"; Appointment none (its rows); Settings none.
5. **Destructive actions go behind ⋯ as text items.** They remain reachable on every page where they exist today (mark, visit, session, appointment, photo, person, trash item, account, webhook, measurement, report, export), never as a red button in the flow and never as a bare icon.
6. **Back is an icon with the parent's name.** The parent's title is the accessible name and the desktop text, so ten hand-written back strings become one pattern.
7. **One tap from Home on a phone:** the camera for any due mark, any person, any coming appointment, Settings. **Two taps:** any mark, adding a mark (a map tap), starting a session, a person's appointment or reports sheet.

Not recommended now: landing a single-person household directly on its person page. It saves one tap in the most common installation but breaks the one model; revisit if the PO finds the hop hurts in use.

## 4. Copy

Every string over 120 characters (32 of 798), with a decision. Rewrites are 60 characters or fewer and keep the descriptive register: what was measured or what will happen, never what it means. Where a disclosure **hint** (shown closed) and the body's **intro** (shown open) say the same thing, the hint stays and the intro goes; those read "remove (hint stays)".

| Key (chars) | Now | Decision |
|---|---|---|
| `chart.descriptorsNote` (234) | Compactness is 1 for a circle and less for any other outline. The colour contrast (ΔE) is relative to the card's grey patch… it describes the photo, not the mark's nature. | Move to a help sheet behind `CircleHelp` beside the table; the sheet keeps the whole text, including "it describes the photo, not the mark's nature". |
| `webhooks.intro` (205) | Send the daily list of marks due for a photo to Home Assistant, ntfy, Gotify, n8n or any address… never photos or notes. | Remove (hint stays: "The daily list of due marks, sent to your own services."); a field note under the form: "Carries names and dates only; never photos or notes." (52) |
| `push.intro` (205) | When marks are due for a photo, this device gets one notification a day, after the reminder hour. The message travels encrypted… | Rewrite: "One notification a day when marks are due." (42). The encryption detail goes to the help sheet. |
| `backups.intro` (197) | An encrypted backup is written every night after {{hour}}:00 into the backups folder of the data directory. Copy that folder… | Rewrite: "Encrypted backup nightly after {{hour}}:00, in the data folder." (60) and a second line "Copy the backups folder to another machine." (43) |
| `sessions.intro` (184) | A session photographs the whole body region by region, in the same order and pose each time… Skip any region you prefer not to photograph. | Remove (hint stays: "The whole body, region by region, to compare over time."). Skipping is explained by the Skip action and the sensitive-region line. |
| `calendar.intro` (179) | Subscribe from your calendar app to see when each mark is due for a photo, and the appointments… over your VPN, with no push service. | Remove (hint stays: "The due dates and appointments in your calendar app."). The VPN detail belongs in the deployment guide. |
| `sessions.experimentalNote` (173) | The experimental analysis is on for this person: after each photo, spots that may be marks are proposed for you to confirm or reject… | Rewrite: "Experimental: proposed spots need your confirmation." (51); shown once per session. |
| `evaluation.quality` (167) | Quality warnings agree with your judgement on {{agreement}} of the photos: {{caught}} of {{poor}} poor photos were warned about… | Move into the results table as rows: "Poor photos warned about: {{caught}} of {{poor}}", "Good photos flagged: {{flagged}} of {{good}}", "Agreement: {{agreement}}". |
| `data.exportIntro` (159) | Choose a passphrase. You will need it to open the file; neVus does not keep it… It opens with the standard age tool. | Rewrite: "A passphrase opens the file. neVus does not keep it." (50). "Opens with age" becomes a tooltip on the field. |
| `accounts.intro` (156) | Who can sign in to this neVus. There is no open registration: you create each account with a temporary password… | Rewrite: "Who can sign in. Accounts get a temporary password." (49). Proxy variant: "Accounts come from your single sign-on." (39) |
| `sessions.blurNote` (154) | The blurred photo takes this one's place. The original is removed at once, not kept in the trash, and cannot be brought back… | Rewrite: "Replaces the photo for good. The marks on it stay." (50) |
| `evaluation.intro` (154) | Label your own photos to see how the analyzers do on them: draw the mark's true outline and say whether the photo is good… | Rewrite: "Outline your photos' marks to measure the analyzers." (52) |
| `data.purgeIntro` (149) | Every mark, visit, measurement and photo of {{name}} will be removed now, without passing through the trash. Export first… | Rewrite: "Removes everything of {{name}} now, skipping the trash." (52 with a short name). The export button sits above it. |
| `proposals.intro` (147) | Made by the experimental analysis turned on for this person. A proposal enters the record only if you use it… | Rewrite: "Experimental proposals. Nothing is recorded until you use one." (58) |
| `reminders.settingsIntro` (146) | Marks due for a photo appear on the home page. You can also receive one email a day when something is due; it lists names and dates, never photos. | Remove; the merged Reminders card's rows say it. A field note under the email row: "Names and dates only, never photos." (34) |
| `compare.differenceNote` (146) | Shaded where the colours differ once the photos are lined up. It shows where to look and measures nothing: light, focus and hair show up here too. | Rewrite: "Colour differences only; it measures nothing." (44). "Light, focus and hair show up too" becomes a tooltip on the ramp. |
| `persons.experimentalHint` (144) | Off by default. When on, neVus may propose outlines and changes on its own; each proposal is labelled experimental and you confirm or reject it. | Rewrite: "Proposes outlines, labelled experimental; you confirm each." (57) |
| `calendar.warning` (142) | This link is shown only now. Anyone with it sees the names of the marks and their dates, so keep it private. Making a new link stops this one. | Rewrite: "Shown once. Anyone with the link sees mark names and dates." (57). "Making a new link stops this one" moves to the "Make a new link" confirmation. |
| `sessions.deleteConfirm` (139) | Delete this session? Its photos go to the trash and the marks found on them are removed from it. The marks themselves stay in the registry. | Rewrite: "Delete this session? Its photos go to the trash; marks stay." (58), in the app's dialog rather than `window.confirm`. |
| `secondFactor.intro` (139) | With a second factor, signing in needs your password and a code from an authenticator app on your phone, so a password alone opens nothing. | Remove (hint stays: "A code from your phone, besides the password."). |
| `images.privacyNote` (134) | The photo stays on this server. Everything the camera embedded except the capture time and orientation is removed before it is stored. | Remove from the visit page: the upload toast (`images.uploaded`) already says it; the full sentence goes to Settings → About. |
| `evaluation.labelIntro` (133) | Outline the mark as it really is. Tap it to fit an outline, or place the points yourself; the dashed line is the analyzer's proposal. | Rewrite: "Tap to fit the outline, or place points yourself." (50); the legend line already explains dashed and solid. |
| `compare.zoomHint` (133) | Pinch or use the mouse wheel to zoom, drag to move; side by side, both photos follow. With a keyboard: + and − zoom, the arrows move. | Remove from the flow; show "+ − zoom · arrows move" as a caption only while the canvas has keyboard focus. |
| `measure.cardTilted` (131) | Reference card found, but tilted {{tilt}}° (limit {{limit}}°). If you can, retake the photo holding the phone parallel to the skin. | Rewrite: "Card tilted {{tilt}}°, over the {{limit}}° limit. Retake if you can." (58) |
| `measure.zoomHint` (127) | Pinch or use the mouse wheel to zoom, drag to move. With a keyboard: + and − zoom, the arrows move, Enter places at the centre. | As `compare.zoomHint`; the Enter rule joins the focus caption. |
| `data.overQuota` (127) | This person's photos use more space than the limit the administrator set. Nothing is refused; consider removing old duplicates. | Rewrite: "Photos exceed the storage limit set by the administrator." (56) |
| `reports.introLesion` (126) | A PDF record of this mark for the clinician: its photos with a scale, the measurements with their uncertainty, and your notes. | Remove (hint stays: "The PDF record of this mark for the clinician."). |
| `auth.claimIntro` (125) | Nobody has an account yet. The first account becomes the administrator and creates the others; there is no open registration. | Rewrite: "This first account becomes the administrator." (44) |
| `app.intendedUse` (123) | neVus is a personal documentation and measurement aid. It does not diagnose, screen for, or assess the risk of any disease. | Keep verbatim. It is the intended-use statement (PRD §2) and stays reachable in Settings → About (unfolded) and in every report's footer. |
| `card.intro` (122) | Print it, cut it out and place its window over the mark when you take a photo: neVus reads the scale and the tilt from it. | Rewrite: "Print it and place its window over the mark in photos." (52) |
| `evaluation.command` (121) | These figures use the proposals already made. To run the current analyzer afresh on every labelled photo: nevus evaluate. | Rewrite: "Figures use existing proposals. To rerun: nevus evaluate." (56) |
| `appointments.intro` (121) | Planning to see a clinician? Enter the date: neVus lists the marks to photograph before it and makes the report to bring. | Remove (hint stays: "Plan the photos before a consultation and take the report along."). |

Shorter strings that sit on every-use pages and are worth the same pass: `observations.notesHint` (86) → "In your own words." (18); `sessions.howTo` (118) → "Same light and distance each time. Use the timer for the back." (62, shown once); `quality.hint` → "Kept as it is. Retake if you can." (33); `capture.lastTime` → "Last time: match distance and angle." (36); `lesions.placingHint` (84) → "Tap the zone, then the exact spot." (34); `offline.quickIntro` → "Offline. Photos are kept here and upload later." (47); `auth.codeIntro` / `auth.recoveryIntro` → "The six-digit code from your authenticator app." (47) / "A recovery code you saved. Each works once." (43).

Two boundary statements stay on purpose, because they sit where a user might read meaning into a number: `measure.disclaimer` (73, "A measurement describes size. It says nothing about what the mark is.") on the measure page, and the intended-use statement in About. The "never interprets it" clause of the notes hint and the "measures nothing" of the difference note draw the same line; the first can go (About says it), the second stays because it sits under a picture that invites interpretation.

## 5. Icon policy

Icons come from Lucide only (`lucide-react` is already a dependency). Every icon button has an accessible name equal to the text it replaces, shown as a tooltip; "desktop label" means the text also appears from 900 px, the breakpoint the layouts already use. The untracked `IconButton` (with a `showLabel: "desktop"` mode) and `Menu` (with `MoreHorizontal`) in this branch's working tree fit the policy as written.

### Controls that become icon buttons

| Control today | Screens | Lucide | Accessible name | Desktop label |
|---|---|---|---|---|
| Back / Back to the person / Back to {{lesion}} / Back to the visit / Back to the mark / Back to the session / Back to settings / Back to the settings / Back to the evaluation set / Back to {{name}} | every inner page | `ArrowLeft` | "Back to <parent's title>" | yes (the parent's title) |
| Zoom in / Zoom out / Show the whole body | person | `ZoomIn` / `ZoomOut` / `Maximize` | as today | no (already icon buttons; replace the glyphs) |
| Cancel (placing) | person | `X` | "Cancel placing" | yes |
| Edit details | mark | `Pencil` | "Edit details" | yes |
| Not now: In a week / In a month | mark | `BellOff` opening a two-item menu | "Not now" | yes |
| Compare visits | mark | `Columns2` | "Compare visits" | yes |
| Show as a table / Show as a chart | mark | `Table` / `ChartLine` | as today | yes |
| Download as CSV | mark | `Download` | "Download as CSV" | yes ("CSV") |
| Download the PDF (N pages, size) | mark, person reports, appointment | `Download` | "Download the PDF" | yes; pages and size as the row's text |
| Take a photo + Live camera (merged), once a photo exists | visit | `Camera` | "Take a photo" | yes |
| Choose a file | visit | `ImagePlus` | "Add from files" | yes |
| Delete (a measurement) | visit | `X` | "Delete this measurement" | no (row action) |
| Close | photo preview, live camera | `X` | "Close" | no |
| Torch | live camera | `Flashlight` | "Torch" | yes |
| Photograph now | appointment rows, home due rows | `Camera` | "Photograph {{mark}} now" | yes |
| Take it again | zone page | `Camera` | "Take the photo again" | yes |
| Blur a part of the photo | zone | `EyeOff` | "Blur part of the photo" | yes |
| Remove the last area / Remove the last point | zone blur, label page | `Undo2` | as today | yes |
| Clear the outline / Start again / Outline again | label page, measure | `RotateCcw` | as today | yes |
| Adjust as a circle | measure | `Circle` | "Adjust as a circle" | yes |
| Copy the link → Copied | calendar sheet | `Copy` → `Check` | "Copy the link" | yes |
| Save as a file (recovery codes) | settings | `Download` | "Save as a file" | yes |
| Send a test (webhook row) | settings | `Send` | "Send a test to {{name}}" | yes |
| More (new): the ⋯ menu holding Move to the trash, Delete the session, Delete the appointment, Change the date or the note, Delete now, the per-account actions, per-webhook Delete, Calendar link, Profile settings, PDF record | mark, visit, session, appointment, trash, settings, person | `MoreHorizontal` | "More actions" | no (the items carry text) |

### Text that gains a leading icon and keeps its words

"Add a person" (`UserPlus`), "Add a mark" (`Plus`), "New visit" (`Camera`), "Measure" (`Ruler`), "Use the reference card" / "Use a coin" / "Use a known length" (`CreditCard` / `Coins` / `Ruler`), "Open the trash" (`Trash2`), "Sign out" (`LogOut`), the tool chips "Appointment" / "Session" / "Reports" (`CalendarPlus` / `PersonStanding` / `FileText`). The icon helps recognition; the text carries the meaning.

### Controls that stay text, and why

| Control | Reason |
|---|---|
| Delete for good; Delete now; Blur N areas; Turn it off (second factor); Stop the link; Finish the session; Move … to the trash and Delete the session / appointment (as menu items); Remove from this photo; Not a mark | Irreversible or consequential: the word is the confirmation. Trash moves are recoverable, but the rule that destructive actions stand apart holds; as text items in a menu, they do. |
| Create the administrator; Turn the second factor on; I have saved them; Keep this visit; Yes, it is that mark; Use this measurement | Consent or acknowledgement: the user must read what they agree to. |
| Side by side / On top / Slider / Differences; Front / Back / Head / Hands / Feet; To label / Labelled / All; Longest diameter / Area / Compactness / Colour contrast; Scale / The mark | Mutually exclusive options whose icons would be ambiguous (On top against Slider; Area against Compactness). Short words; they fit a phone as a segmented control. |
| Skip; Photograph it after all; Link to it; Record a new mark; Use this coin; Use this length; Change the scale; Remind me again; Restore; Start from the proposal | Taken at a decision point and ambiguous as icons; a wrong tap costs a step. |
| Start a session; Add the appointment; Make the summary / the record / the report; Make a calendar link; Make the export; Set up a second factor; New recovery codes; Back up now; Read the latest backup back now; Add the webhook; Create the account; Set a new password; Enable / Disable; Send a test (email) | Once a season or once ever: no habit forms to learn an icon by, and the label is the explanation. |
| Save; Continue; Sign in; Create the mark; Save the measurement; Save the label | Form submits: text by convention. |
| Download for A4 paper / Download for US Letter paper | Two downloads of the same thing differ only in words. |

## 6. Inconsistencies, and the one pattern to adopt

| What | Where it differs | Pattern |
|---|---|---|
| Back links | "Back" (person); "Back to the person" (mark, session); "Back to {{lesion}}" (visit); "Back to the visit" (measure); "Back to the mark" (compare); "Back to the session" (zone, sessions compare); "Back to settings" (trash) against "Back to the settings" (evaluation); "Back to the evaluation set" (label); "Back to {{name}}" (appointment) | One `ArrowLeft` whose name and desktop text is "Back to <parent's title>", built from the parent's title, never hand-written. |
| Removing things | "Move the mark to the trash", "Move visit to trash" (no article), "Move to trash" (photo), "Delete" (measurement, report, webhook), "Delete now" (trash), "Delete the appointment", "Delete the session", "Delete for good" (person), "Remove" (export, mark from a photo), "Reject" (proposal) | "Move to the trash" for anything the trash page can restore (mark, visit, photo); "Delete" for anything it cannot (measurement, report, webhook, appointment, session, export), the dialog saying what goes; "Remove from this photo" only where the mark itself survives. Always with the article. |
| The due vocabulary | Home: "Due for a photo", "due today", "due since {date}". Mark: "Check every", "Next check", badge "Due" / "In 90 days". Appointment: "Due on {date}", "Never photographed", "To photograph before the appointment" | The thing that is due is a photo: "Photo every 3 months", "Next photo", "Due for a photo", "Due on". Drop "check", which reads as an examination. |
| Quality warnings | A "!" dot on the thumbnail (visit page); an amber chip "Quality warnings" on visit rows (mark page); a boxed notice "Saved with quality warnings" under the hero | The dot on every thumbnail; the notice only on the visit page, as the photo's caption; no chip. |
| Headings that repeat their content | "Body map" above the map; "Photos" above the photo; "Visits" above the timeline and "Marks" above the list (these two carry a tool or separate lists and stay) | A heading only where it carries a tool or separates two lists. |
| Hints and intros | Twelve tools carry both a one-line hint (closed) and a one-to-three-sentence intro (open) saying the same thing: appointments, sessions, calendar, reports (person and mark), second factor, reference card, your data, accounts, email delivery, webhooks, backups | One line per tool, the hint; detail on demand behind `CircleHelp` where it must survive. |
| "(administrator)" suffix | Accounts, Email delivery, Backups, Instance carry it; Webhooks (also admin-only) does not; the export says "Export the whole instance (administrator)" | One "Administration" group visible only to administrators; no suffixes. |
| "Experimental" marking | A chip in the Proposals heading; "(experimental)" in the push card's title; a sentence on the session page; a plain label in Profile settings | One chip "Experimental" after the title, everywhere. |
| Make / Create / Add / Start / Prepare | "Make the summary / the record / the report / a calendar link / a new link"; "Create the mark / the account / Create"; "Add a person / a mark / the webhook"; "Start a session / the export"; "Prepare the appointment" | "Add" for records the user owns (person, mark, webhook, account, appointment); "Make" for generated artefacts (report, link, export); "Start" for processes (session). So "Prepare the appointment" → "Add the appointment", "Start the export" → "Make the export", "Create the account" → "Add the account". |
| Saving | Appearance saves on change; the Reminders e-mail and the Reference card have a "Save"; the visit's notes have a "Save"; the e-mail server has a "Save" and a separate test form | Selects and switches save on change; text fields save with one "Save" per form; never two "Save" buttons in one card. |
| Links that look like buttons | "Measure on the photo" is a link with the primary button's styling; "Compare visits" and "Download as CSV" are plain links beside buttons; "Photograph it after all" is a quiet button | Actions are buttons; navigation is links; a link never borrows a button's look. |
| Region and zone | The map says "zone" ("Tap a zone to select it"); the session says "region"; the zone page's new-mark form picks a map zone without naming it | Keep both words (they are different things) but name the second once: "Or record a new mark in [zone of the body map]". |
| Confirmations | `window.confirm` for deleting a session; the app's dialog for the password; nothing for trash moves | The app's dialog for everything irreversible; nothing for trash moves (the trash is the undo). |
| Compare titles | "Compare: Chest mark" against "Two sessions, region by region" | "Compare: Chest mark" / "Compare: sessions of 5 Oct and 12 Nov". |

## 7. The twenty changes that cut the most clutter for the effort

Ranked by targets and lines removed over effort. S: a day or less; M: a few days; L: a week or more.

| # | Change | Screens | Size |
|---|---|---|---|
| 1 | Session page shows one region at a time: the current region's card with its pose, "Take the photo" and "Skip"; the other seventeen as a compact progress list. Finish and Delete behind ⋯. 52 → 4 targets, 4.4 → about 1.3 viewports. | 13 | M |
| 2 | Settings: members' groups within little more than one viewport, administrator groups under one "Administration" fold, section pills removed on the phone, Reminders and Notifications merged into one card of channel rows. 29 → 13 targets. | 17–20 | M |
| 3 | Person page tools: five disclosure cards become one row of three chips (Appointment, Session, Reports) and a ⋯ (Calendar link, Profile settings); live cards for an appointment ahead or a session in progress. | 04, 05, 05b, 12 | M |
| 4 | Destructive actions and rare edits behind ⋯ with text items: mark, visit, session, appointment, trash items, accounts, webhooks. No red button in any flow. | 06, 07, 08, 13, 22, appointment, settings | S |
| 5 | Back links become `ArrowLeft` with the parent's title; one component on every inner page. | all inner pages | S |
| 6 | Due rows on Home carry `Camera` "Photograph now", reusing `useStartVisit`. The most frequent task: 3 taps → 1. | 03 | S |
| 7 | The measure page starts at the mark step when the card is found and within the tilt limit; "Change the scale" is a quiet action. A measured visit: 7 taps → 4. | measure | S |
| 8 | Visit toolbar: "Take a photo" and "Live camera" merged into one `Camera`; "Choose a file" → `ImagePlus`; "Kind" moved to the per-photo preview; the privacy note removed (the toast keeps it). | 07 | S |
| 9 | Delete every intro that repeats a disclosure hint (twelve) and the two zoom hints; add `CircleHelp` where detail must survive (descriptors, push encryption, the export tool). | 04–08, 12, 17, compare, measure | S |
| 10 | Mark page: Edit → `Pencil`; Compare → `Columns2` on the Visits heading; snooze → `BellOff` menu; Reports → a ⋯ item opening a sheet; table and CSV → icons. 17 → 10 targets. | 06, 08 | S |
| 11 | Tapping a map zone starts placing (zone → zoom → spot), "Add a mark" stays as the visible primary, "Cancel" → `X` in the map's corner. Adding a mark: 5 taps and a scroll → 4. | 04, 05, 05b, 12 | M |
| 12 | Reports and the appointment report: Language and Paper default from Settings (the UI language; the paper chosen once) behind "Options"; one "Make" button. | 08, person reports, appointment | S |
| 13 | Appointment page: "Photograph now" → `Camera` per row with a desktop label; edit and delete → ⋯; the report intro removed. | appointment | S |
| 14 | Zone page: the link chooser shown once and folded behind "Change the link…" for a linked mark; "Record a new mark instead" as a disclosure in the tapped-mark panel; Blur → `EyeOff` in the photo's toolbar. 10 → 5 targets. | 14, 15 | S |
| 15 | Rename "Check every / Next check" → "Photo every / Next photo"; hide facts with no value. | 06, 08, mark list | S |
| 16 | Visit rows: the "Quality warnings" chip becomes the amber dot on the thumbnail; symptom chips stay. | 08 | S |
| 17 | Visit page: title is the mark's name with the date as subtitle; the "Photos" heading removed; the notes hint "In your own words."; symptoms as one row of toggle chips. | 07 | S |
| 18 | Home: "Add a person" becomes a quiet `UserPlus` row at the end of the list; person cards show "N due". | 02, 03 | S |
| 19 | Second-factor set-up: the three numbered steps become one line; "Save as a file" → `Download` with a label; the accounts rows' three actions → ⋯. | 19, 20, settings | S |
| 20 | The 32 long strings rewritten or moved as in section 4, in `en.json`, `es.json` and `pt.json`. | all | S |

Items 1, 2, 3 and 11 are the medium ones; the other sixteen are a day each or less. Together they take the 27 phone sheets from 309 targets to 191, and the three longest pages (session, settings, mark) from 4.4, 3.1 and 2.3 viewports to roughly 1.3, 1.2 and 1.8.
