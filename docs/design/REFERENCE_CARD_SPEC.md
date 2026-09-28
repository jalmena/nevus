# neVus reference card — specification

Baseline 2026-09-23. The reference card is the primary scale reference for measurements (requirement FR-MEA-01). It is a printed, credit-card-sized object placed next to, or around, the mark being photographed. It gives the analyzer millimetres per pixel, the tilt of the skin plane relative to the camera, and a neutral colour reference. This document specifies its geometry, printing, detection requirements and the generator that produces it. Coins and a manual line remain as fallbacks.

## 1. Why a printed card

- Fiducial markers are detected with sub-pixel corner accuracy and give a full pose (homography), so foreshortening from camera tilt can be corrected or gated; a coin only gives a circle whose apparent radius shrinks with tilt.
- Wound-care studies report better inter-rater reliability for adhesive markers than for rulers; averaging scale over several markers reduces perspective error.
- The card also carries grey and white patches for exposure and white-balance checks, which coins cannot provide.

## 2. Variants

| Variant | Size | Purpose |
| --- | --- | --- |
| **Window card** (primary) | 85.6 × 54.0 mm (ISO/IEC 7810 ID-1), with a 24 mm circular aperture | Placed over the mark so that the reference plane is the skin plane at the lesion; the aperture edge carries millimetre ticks |
| **Strip** | 60 × 20 mm | For places where the window card cannot lie flat (fingers, ears, nose); placed beside the mark |

Both variants share the marker dictionary, the colour patches and the print-verification scale.

## 3. Geometry of the window card

Coordinates in millimetres from the top-left corner of the card; the card outline itself is a 0.3 mm black rule for cutting.

| Element | Position and size | Notes |
| --- | --- | --- |
| Aperture | circle Ø 24.0 mm centred at (42.8, 27.0) | Cut out; edge ring 1.5 mm wide printed in ink with ticks every 1 mm (2 mm long) and every 5 mm (3 mm long) on the outside |
| Fiducial markers | four ArUco markers from `DICT_4X4_50`, ids 0, 1, 2, 3, 12.0 mm square, at the four corners of a 60 × 40 mm rectangle centred on the aperture: centres at (12.8, 7.0), (72.8, 7.0), (12.8, 47.0), (72.8, 47.0) | 1.5 mm white quiet zone around each marker; marker ids are fixed so the analyzer knows the card orientation |
| Grey patch | 10 × 10 mm at (78.0, 22.0) to (85.0 − 1.5 margin) → use (74.0, 22.0) size 8 × 8 mm | 18 % reflectance neutral grey (`#777777` in sRGB print terms; verify with the printer profile) for exposure reference |
| White patch | 8 × 8 mm at (74.0, 32.0) | Paper white, for white balance |
| Print-verification scale | 50.0 mm line with end ticks along the bottom edge from (17.8, 51.0) to (67.8, 51.0) | The person measures it with a ruler after printing; if it is not 50 ± 0.5 mm the printer scaled the page |
| Wordmark and id | `neVus` wordmark 14 mm wide at (4.0, 50.0) and the text `card v1 · 24 mm` in 2 mm type | Card version is read by the analyzer from the marker ids (v1 = ids 0–3); the text is for humans |

Strip variant: two markers (ids 4 and 5, 12 mm) at each end of a 60 × 20 mm strip, a 30 mm scale bar with 1 mm ticks between them, grey and white patches of 6 × 6 mm.

## 4. Printing

- Print at 100 % scale ("actual size", no fit-to-page) on A4 or US Letter; the generator produces both page sizes with two window cards and two strips per sheet, plus the verification instruction in English and Spanish.
- Paper: matte card stock (200–300 g/m²) or matte photo paper; glossy paper and glossy lamination cause specular highlights that break marker detection. If laminating, use matte laminate.
- Cutting: along the 0.3 mm outline; the aperture with a craft knife or a 24 mm punch. Rounded corners are optional.
- Verification: after printing and before first use, measure the 50 mm line; the app's onboarding asks for this and offers a way to record the measured length so the analyzer can apply a correction factor (for example 49.6 mm measured → scale ×1.008).
- Hygiene: the card touches skin; it is personal, wiped with alcohol, and replaced when worn (faded markers lower detection confidence, which the app reports).

## 5. Detection requirements for the analyzer (`scale.card`)

- Input: the full-resolution scrubbed original.
- Detect ArUco markers of `DICT_4X4_50` with corner refinement; require at least two markers with known ids from the same card version; estimate the homography from all detected marker corners to the card's millimetre coordinates.
- Scale: millimetres per pixel at the aperture centre from the homography; uncertainty from the corner reprojection residuals and the number of markers (propagated as σ_scale, relative).
- Tilt: from the homography decomposition; the measurement is flagged when the tilt exceeds 15° (configurable) and the person is invited to retake.
- Minimum marker size: 40 px across in the image for reliable detection; at 12 mm this implies at least 3.3 px/mm, so a 24 mm aperture spans at least 80 px. The framing check warns when markers are too small (too far) or cut off.
- Colour: median RGB of the grey and white patches recorded with the analysis for exposure and white-balance checks; no colour correction is applied to stored images, only to derived analyses and comparison views, and always reversibly.
- Outputs recorded in the analysis: marker ids and corners, homography, mm per pixel and its σ, tilt, patch values, card version, correction factor applied.

## 6. Coin fallback (`scale.coin`)

Euro coins by diameter: 1 c 16.25 mm, 2 c 18.75 mm, 5 c 21.25 mm, 10 c 19.75 mm, 20 c 22.25 mm, 50 c 24.25 mm, 1 € 23.25 mm, 2 € 25.75 mm. The person taps the coin, the analyzer fits a circle (ported from MoleMapper's approach, rescaled to full resolution), the person picks the denomination and may adjust the circle. Uncertainty includes the fit residual and an unknown-tilt term (a coin cannot reveal tilt, so σ_scale is larger than with the card; the interface says so).

## 7. Manual fallback (`scale.manual`)

Two points placed by the person on an object of known length (a ruler mark, the card edge, a coin diameter) with the length typed in millimetres. Uncertainty from placement precision at the image resolution plus an unknown-tilt term.

## 8. Generator

A script in the backend project (`nevus card --page a4|letter --out cards.pdf`) draws the cards with OpenCV's ArUco module for the markers and vector primitives for everything else, rendered to PDF at exact millimetre dimensions, and embeds the bilingual verification instructions. The same geometry constants feed the analyzer, so the card and its detector cannot disagree. The generated PDFs for version 1 are published as release assets and linked from the deployment guide and the in-app onboarding.

## 9. Evaluation

Fixture photographs of a printed card next to discs of known diameter (3, 5, 8 and 12 mm) at 8, 12 and 18 cm, at 0°, 10°, 20° and 30° tilt, under warm, cool and mixed light, on paper backgrounds of several tones. Gates in CI: detection rate ≥ 0.98 at ≤ 20° tilt; millimetre-per-pixel error ≤ 2 % at ≤ 15° tilt; disc diameter error ≤ 0.3 mm for the 5 mm disc within the tilt limit; correct tilt flagging beyond it. The Product Owner's own card photographs at known distances join the evaluation set without leaving the server.
