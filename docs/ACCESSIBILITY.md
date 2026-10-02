# Accessibility

neVus aims at WCAG 2.2 level AA on phones and desktops, in both colour schemes, with a keyboard and with a screen reader. This page says how that is checked, what the checks found for 1.0.0, and what they do not cover.

## How it is checked

- Every build runs axe-core with the WCAG 2.0, 2.1 and 2.2 A and AA rules on the pages of the end-to-end journey (`frontend/e2e/journey.spec.ts`), in a phone-sized browser; a serious or critical finding fails the build.
- The screenshot gallery sweeps every screen of the application (26 screens, both colour schemes, a phone and a desktop) with axe, best practices included, when run with `NEVUS_SHOTS_AXE=1`, and writes the findings next to the screenshots (`frontend/.screenshots/a11y-<device>.json`). It runs before a release and after a change to the interface, together with a look at the screenshots themselves (`DEVELOPMENT.md`, "Looking at the design").
- The journey drives by keyboard the parts that are hardest for assistive technology: the size chart as a slider with arrow keys and a spoken value, the comparison modes as a radio group, the body map's zones and the photo canvas.
- Colour comes from one token file, with the contrast of every text colour on every background noted where it is close to the limit, in both schemes; the chart colour passed the colour-vision checks of the data-visualisation palette.

## Results for 1.0.0

- axe: no findings over 26 screens in two colour schemes on two devices (2 October 2026). On the way there: the claim and sign-in pages had no main landmark; skipped regions of a session were dimmed with opacity, below the contrast minimum; the document language was fixed to English whatever the interface language; earlier, hovered links lost contrast and the badges on the attention colour were below the minimum.
- Keyboard: every control is a native button, link or input. The body map's zones are buttons: while a mark is being placed, Enter zooms in on the zone and Enter again places the mark at the zone's anchor; the whole-body button steps back out. The photo canvas is an application region: `+` and `−` zoom, the arrows pan, Enter acts at the centre of the view. Clusters of marks on the map are buttons that zoom in. Dialogs (the password confirmation) trap focus and close with Escape.
- Screen readers: landmarks (banner, navigation, main), one first-level heading per page, labelled fields with their hints and errors attached, status messages for work in progress, decorative images with an empty alternative and meaningful ones described (the mark's crop, the QR code, with the same secret written out beside it). The list of marks mirrors the markers on the map, the chart has a table and a CSV, and every proposal of the experimental analysis carries words, not only a colour or a shape.
- Motion and colour: transitions last 120 to 200 ms and stop under `prefers-reduced-motion`. Colour is never the only carrier: due marks say so, difference maps have a legend and a sentence, markers have labels.
- Touch: targets are at least 44 pixels; the map and the photo canvas accept pinch and drag as well as the buttons.
- Language: the interface is in English or Spanish per account, and the document language follows, so speech uses the right voice.

## Known limitations

- Placing a mark, or an area to blur, by keyboard lands at the zone's anchor or at the centre of the view: pan and zoom first (arrows, `+`, `−`) for precision. A pointer is more precise; nothing depends on the exact spot except the person's own record.
- The overlay and difference views are visual aids with a text description of what they show; there is no non-visual equivalent of the image itself.
- Reports are PDF/A-3b with the data attached as JSON; they are not tagged for PDF/UA.
- The checks are automated and by the developers. A pass by people who use a screen reader or a switch every day has not happened yet; findings are welcome as issues.
