# neVus — Design brief

Baseline 2026-09-23. This brief sets the visual language and the interaction model of neVus before the first screen is built. It follows the Product Owner's answers (warm neutrals with one calm accent, flat schematic body silhouette, calm in-app tone, quiet humanist typeface, three mark directions to sketch) and the requirements in [`PRODUCT_REQUIREMENTS.md`](../../PRODUCT_REQUIREMENTS.md). Tokens defined here become `frontend/src/design-system/tokens/tokens.css` and are shared with the PDF templates.

## 1. Principles

1. **Observation, not alarm.** The interface records and shows; it never warns about health. Colour, motion and copy stay calm even when numbers change.
2. **Continuity.** Time is the second dimension of everything: timelines, comparisons, rings and dates are first-class visual elements.
3. **Precision with honesty.** Every measurement shows its uncertainty by default; scale bars accompany every image; nothing pretends to be more exact than it is.
4. **The photograph is the hero.** Skin tones and lesion colours must not be distorted by the surrounding interface: neutral, low-saturation surfaces around images, no coloured overlays on photographs except explicit tools.
5. **One hand, one thumb.** Capture happens with a phone held in one hand in front of a mirror; primary actions live in the thumb zone; every step is undoable.
6. **Private by design, visibly.** Locks, exports and deletions are explained in plain words; nothing leaves the server without an explicit action.

Visual metaphors: the dot under watch, rings of time, the letter V as two lines of sight. Avoided: crosses, hearts, pulses, red alerts, stethoscopes, anything from emergency or hospital iconography.

## 2. Brand

- Name: **neVus**, always set with a lowercase n and e, a capital V, lowercase u and s. Identifiers stay `nevus`.
- Tagline: **"Because 'I think it was smaller' is not data."** Used on the login page, the store card and the report footer. Other lines ("Evidence, not memory.", "Your moles, on the record.") may appear in the README.
- Mark: **the divider**, a measuring compass holding the mark between its points; the legs are the V of the name, the hinge carries a hole of half its diameter in the inverse colour, the mark between the points is the only accent. Settled after five rounds; sources and usage rules in [`brand/identity/README.md`](brand/identity/README.md).
- Wordmark: `neVus` in B612 Bold with the mark standing in for the V, optically centred so the mark's axis is the centre of the word.
- The mark and the wordmark are always presented on the dark paper (`#17161A`), whatever the interface theme: app icon, favicon, login page, report header, store card and README. Light drawings exist only for a small inline mark on light surfaces.
- Tone: the sarcastic register lives in the README and marketing copy; in-app text is calm, short and descriptive (rules in the requirements, section 7).

## 3. Colour

Warm neutrals with one calm accent. Red is reserved for system errors (failed upload, server unreachable) and is never used for lesions, measurements, due states or comparisons.

| Token | Light | Dark | Use |
| --- | --- | --- | --- |
| `--color-paper` | `#F6F1EA` | `#17161A` | page background |
| `--color-surface` | `#FFFCF7` | `#1F1E23` | cards, sheets |
| `--color-surface-2` | `#EFE8DE` | `#2A292F` | secondary surfaces, table stripes |
| `--color-border` | `#D9D1C5` | `#3A393F` | hairlines |
| `--color-ink` | `#2B2A28` | `#EDE8E0` | primary text |
| `--color-ink-2` | `#5E5A54` | `#B9B3AA` | secondary text |
| `--color-ink-3` | `#8B857C` | `#8A857D` | tertiary text, placeholders |
| `--color-accent` | `#1F6F6B` | `#5FB3AE` | primary actions, selected marker, the V |
| `--color-accent-2` | `#DDEDEA` | `#1B3735` | accent tint surfaces |
| `--color-info` | `#3E6D9C` | `#8DB4DE` | neutral information |
| `--color-attention` | `#B9791B` | `#E3B25F` | due items, quality warnings (amber, not red) |
| `--color-danger` | `#A8402F` | `#E07A67` | system errors only, destructive confirmation |
| `--color-success` | `#4E7D3A` | `#8FBF7A` | saved, synced, verified |
| `--color-photo-frame` | `#E9E3DA` | `#2E2D33` | surface around photographs |
| `--color-marker` | `#2B2A28` | `#EDE8E0` | body-map markers (unselected) |
| `--color-marker-selected` | `#1F6F6B` | `#5FB3AE` | selected marker |
| `--color-chart-1..4` | `#1F6F6B`, `#8A6D3B`, `#3E6D9C`, `#6B5B95` | adjusted for dark | measurement series |

Contrast: every text/background pair meets WCAG 2.2 AA (4.5:1 body, 3:1 large text and UI components); the tokens above are chosen for that and verified in Storybook. The theme follows the system by default and can be fixed per user.

## 4. Typography

- Interface family: **Epilogue** (SIL Open Font License 1.1), variable weight, self-hosted as WOFF2. Body text 500, secondary text 400, emphasis and buttons 600; tabular figures (`tnum`) for measurements, dates and tables. **B612** is used for the wordmark only. No font is loaded from third parties at runtime; `system-ui` is the fallback stack.
- Weights: 400 (secondary text), 500 (body), 600 (headings, buttons). No 700 in the interface.
- Scale (rem, 16 px base): 0.75 / 0.875 / 1 / 1.125 / 1.375 / 1.75 / 2.25. Line heights 1.5 for text, 1.2 for headings.
- Numbers: `font-variant-numeric: tabular-nums` for measurements, dates and tables so columns align; the ± sign and unit set in secondary ink.
- Dates: absolute (`12 Mar 2026`) with a relative hint (`6 months ago`) where it helps; never only relative.

## 5. Space, shape, elevation, motion

- Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64 px (`--space-1` … `--space-8`).
- Radii: 6 px controls, 12 px cards and sheets, 999 px pills; the mark's container uses 22 %.
- Elevation: borders first; two shadow levels (`--shadow-1` for cards on paper, `--shadow-2` for sheets and dialogs); no shadows on photographs.
- Motion: 120 ms for state changes, 200 ms for panels, 320 ms for sheets; easing `cubic-bezier(0.2, 0, 0, 1)`; every animation respects `prefers-reduced-motion`.
- Touch targets: at least 44 × 44 px; primary actions within thumb reach on phones.

## 6. Iconography

Outline icons at 1.5 px stroke from a libre set (Lucide, ISC licence), 24 px grid, tinted with the current ink. Custom glyphs: the lesion marker (dot with ring), the reference card, quality states (focus, light, framing, distance), the V mark. No filled red icons anywhere.

## 7. Components

Core: button (primary, secondary, quiet, destructive with confirmation), icon button, input with inline validation, select, switch, segmented control, chip (tags, quality flags), card, list row, bottom sheet (mobile) / dialog (desktop), toast (non-blocking, never for health content), skeleton loaders, empty state (illustration-free: a sentence, a reason and one action), inline error state with retry.

Domain: body map (zones, markers, clusters, zoom controls, list alternative for screen readers), lesion header (label, location, status, next due), timeline (date rail, thumbnails, measurement chips with ±, quality flags, notes), capture stepper (role → photo → quality → reference → measure → confirm), measurement editor (handles for diameter and outline, live ± readout), image compare (side-by-side with synced zoom and scale bars, overlay with opacity slider, wipe slider, difference view labelled as an aid), measurement chart (uncertainty bands, "no detectable change" shading), reminder row with snooze, "Prepare my visit" checklist, report preview, settings groups.

Every component documents its states: default, hover, focus-visible, active, disabled, loading, error, empty, and its dark-theme rendering.

## 8. Layout and navigation

- Mobile first: 360 px minimum width; breakpoints at 600 (large phone, small tablet), 900 (tablet, two panes) and 1200 px (desktop).
- Phone navigation: bottom bar with four destinations: **Map**, **Due**, **Add** (centre, capture), **Visit** (prepare my visit and reports); **Settings** and the person switcher in the top bar.
- Desktop: two panes, body map on the left, detail on the right; the same components, larger.
- Person switcher always visible when the user manages more than one person; the active person's name appears in the top bar and on every capture step to avoid filing a photo under the wrong person.

## 9. Core flow wireframes

Home (phone):

```text
┌────────────────────────────────┐
│ ● Ana ▾                 ⚙  ⋯  │  top bar: person switcher, settings
│                                │
│   [ front ]  [ back ]          │  segmented control
│                                │
│        ┌──────────┐            │
│        │  ○   ○   │            │  body silhouette, zones tappable,
│        │    ▣     │            │  markers: ○ tracked, ▣ selected,
│        │  ○     ◐ │            │  ◐ due for a new photo
│        │          │            │
│        └──────────┘            │
│                                │
│ Due soon                        │  compact strip
│ ◐ Left forearm · 3 months ago   │
│ ◐ Right shoulder · 7 months ago │
│ Visit: 14 Oct · 2 of 5 ready    │
├────────────────────────────────┤
│  Map     Due    (+)   Visit    │  bottom bar
└────────────────────────────────┘
```

Capture (from a lesion or from Add):

```text
1 Role          2 Photo            3 Quality             4 Reference          5 Measure            6 Confirm
┌──────────┐    ┌──────────┐       ┌──────────┐          ┌──────────┐         ┌──────────┐         ┌──────────┐
│Overview  │    │ previous │       │ ✓ focus  │          │ card ✓   │         │  ⊙ drag  │         │ 4.4 ±0.3 │
│Close-up ●│ →  │ overlay  │  →    │ ✓ light  │   →      │ tilt 6°  │   →     │  handles │   →     │ mm       │
│With ref. │    │ (guide)  │       │ ⚠ framing│          │ 0.041mm/px│        │  outline │         │ notes    │
│          │    │ [shutter]│       │ save anyway│         │ or coin ▾│         │ ± live   │         │ [Save]   │
└──────────┘    └──────────┘       └──────────┘          └──────────┘         └──────────┘         └──────────┘
```

Lesion page:

```text
┌────────────────────────────────┐
│ ← Left forearm · "Comet"       │
│ mole · tracked since Jan 2025  │
│ 4.4 ± 0.3 mm · next: 12 Dec    │
│ [Add observation] [Compare]    │
├────────────────────────────────┤
│ 2026 ─┬─ 12 Sep  ▣ 4.4 ±0.3 mm │  timeline rail
│       │  "slightly itchy"      │
│       ├─ 12 Jun  ▣ 4.3 ±0.3 mm │
│       │  ⚠ saved with warnings │
│ 2025 ─┼─ 03 Jan  ▣ 4.1 ±0.4 mm │
│ no detectable change since Jan │  computed from uncertainties
└────────────────────────────────┘
```

Compare:

```text
┌────────────────────────────────┐
│ 12 Jun 2026      ⇄   12 Sep 2026│
│ ┌────────────┐   ┌────────────┐ │
│ │   photo    │   │   photo    │ │  synced zoom, scale bars
│ │ ──5 mm──   │   │ ──5 mm──   │ │
│ └────────────┘   └────────────┘ │
│ [Side by side] [Overlay] [Wipe] │
│ Δ diameter +0.1 ± 0.4 mm        │
│ no detectable change            │
└────────────────────────────────┘
```

## 10. States

- Empty: one sentence saying what will appear here and one action ("No observations yet. Add the first photo of this mark.").
- Loading: skeletons with the final layout; never spinners over photographs.
- Error: what failed and what to do ("The photo could not be uploaded. It is kept on this device and will retry when you are back online.").
- Quality warnings: amber chips with a reason and a "retake" action; never block unless the file is unreadable.
- Offline: a quiet banner and a count of queued observations; sync status per item.

## 11. Accessibility

WCAG 2.2 AA from the first screen: semantic structure, visible focus (2 px accent ring with paper offset), keyboard operability for every control including the body map (zones as buttons with names; markers reachable in a list), labels and descriptions for all inputs, live regions for quality results and sync status, colour never the only carrier of meaning (icons and text accompany states), reduced-motion support, text resizable to 200 % without loss, touch targets of 44 px, and screenshots of every component checked in Storybook with an accessibility add-on.

## 12. Store and marketing assets

Following the Tabernacle convention: `icon.svg` as the single source of the mark, a 512 px PNG generated from it, a 1200 × 630 store card rendered from an HTML file with the real typeface so the card and the application cannot drift apart, and three screenshots (home with the body map, a lesion timeline, a comparison) in the light theme on a phone frame.

## 13. Decisions taken with the Product Owner

1. Mark: the divider (2026-09-23, after five rounds).
2. Wordmark: B612 Bold with the mark as the V, optically centred.
3. Interface typeface: Epilogue 400/500/600 with tabular figures.
4. Tagline: "Because 'I think it was smaller' is not data."

Remaining: none for the identity; the interface components follow this brief.
