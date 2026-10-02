# Model card: the neVus analyzers

neVus measures and documents skin marks; it never classifies them. Every analyzer here outputs a description of a photograph: a warning about the photo, a scale, an outline or an alignment. None outputs a diagnosis, a risk or a recommendation, and none is a learned model. Release 0.3.0 uses classical computer vision only, so there is no training data and nothing is downloaded.

Each result is stored as an append-only analysis record with the analyzer's name, version, parameters and the hash of its input. A newer version adds records and never overwrites old ones (`nevus reanalyze`). Measurements keep the identifier of the analysis that produced them.

| Analyzer | Version | Runs | Output | Decision |
| --- | --- | --- | --- | --- |
| `quality` | 1.0.0 | every photo | warnings: blurry, too dark, overexposed, glare, low resolution | automatic: a warning, never a refusal |
| `scale.card` | 1.0.0 | every photo of a visit | the reference card's homography to millimetres, tilt, scale uncertainty | automatic: a scale the person can replace |
| `fit` | 1.0.0 | when the person taps | a proposed circle or outline around the tap | the person adjusts and saves |
| `segment.auto` | 1.0.0 | only with the experimental analysis on | an outline without a tap, a proposed size, framing hints | **experimental**: pending until the person confirms or rejects it |
| `align` | 1.0.0 | when the person compares two photos | the transform from one photo to the other, or a refusal with a reason | a visual aid; nothing is recorded as a measurement |

## Intended use

Personal documentation of skin marks at home, by the person or their family, to take a consistent record to a clinician. The measurements describe size and its uncertainty; they say nothing about the nature of a mark. Interpretation is for the clinician.

**Out of scope:** diagnosis, triage, risk estimation, deciding whether or when to see a clinician, and use on photos taken by others without their consent.

## `quality` 1.0.0

- **Method**: blur is the exposure-normalised variance of the Laplacian on the sharpest tiles, with a threshold of 15. Exposure is judged from mean lightness and clipping. Glare is small saturated highlights covering less than 2 % of the frame. A short side under 1000 pixels is reported as low resolution.
- **Limits**: a sharp photo of the wrong spot passes. Very dark skin photographed in dim light can read as "too dark", which is correct about the photo but more frequent on darker skin. The person can always keep the photo.

## `scale.card` 1.0.0

- **Method**: ArUco markers printed on the neVus reference card, grouped per physical card. A homography maps the image to the card plane in millimetres. Tilt comes from the anisotropy of that mapping, and the uncertainty combines the fit residual, the print-size check and the card's flatness.
- **Measured** on synthetic photographs (CI): the card is found at every tilt up to 30°. A 5 mm disc in the window measures within 0.3 mm up to the 15° tilt limit. Beyond the limit the measurement is flagged and a retake suggested.
- **Limits**: a card printed at the wrong size is caught only if the person verifies the printed 50 mm line. A curved card (on a curved body part) breaks the flat-plane assumption: the window card limits the error because the mark is seen through it.

## `segment.auto` 1.0.0 (experimental)

- **Method**:
  1. Seed: the reference card's window when the card is in view; otherwise the darkest compact spot in the central 60 % of the photo, with the card itself left out.
  2. With the window card, everything outside the projected window is painted with the skin seen through it, so the card's print cannot join the mark.
  3. Thin dark lines that are long and narrow (hairs) are painted over from their surroundings: a black-hat filter, then inpainting.
  4. The outline is fitted from the seed with the same method as a tap.
  5. Abstention, with a reason, when the region's contrast with its surroundings is below 8 lightness units (`low_contrast`), when it is ragged (`irregular_region`, compactness under 0.35), implausibly large or small, or when nothing stands out (`no_mark_found`).
- **Framing hints** (photos without the card's window): the mark is off centre, too small in the frame, or cut by the edge.
- **Gates in CI** on synthetic close-ups at six steps of the Monk Skin Tone scale (MST 1, 3, 5, 6, 8 and 10), each with and without hairs crossing the mark:
  - a clear mark (half the skin's lightness) is found on every tone, with and without hairs, and its equivalent diameter is within 5 %; the measured error was below 0.3 %;
  - a faint mark (85 % of the skin's lightness) is found within 10 % or the analyzer abstains: it is never confidently wrong. On the darkest tone it abstains more often (`low_contrast`), which is the intended trade-off;
  - a featureless image abstains;
  - with the card, a 5 mm disc is proposed at 5.0 ± 0.3 mm.
- **Limits**: synthetic gates are not a clinical validation. In real photos, expect abstention or poor outlines when:
  - the mark is not darker than the skin (pink or skin-coloured marks);
  - other dark spots (freckles, tattoo ink, shadows) are darker and closer to the middle;
  - specular glare sits on the mark;
  - the border is genuinely gradual.
  Low contrast on darker skin makes faint marks harder to find there; the per-tone evaluation below exists to show it on real photos.
- **Personal evaluation**: an administrator labels photos of the persons they own or manage (an outline and a good or poor quality judgement) under Settings, Evaluation. Then `nevus evaluate` reports, per skin tone, how often a mark was found, the overlap with the label (IoU, Dice) and the diameter error, and how the quality warnings agree with the judgements. The labels never leave the server.

## `align` 1.0.0

- **Method**: when both photos show the card, its homographies give the alignment exactly. Otherwise SIFT features are matched (ratio test) and a homography is fitted with RANSAC. The result is used only with at least 25 agreeing matches, an inlier share of 25 %, and a transform a re-photograph can produce. The difference map compares colour in Lab after exposure matching.
- **Measured** in CI: a synthetic rotation, zoom and shift is recovered within 1.5 pixels, and unrelated photos are refused.
- **Limits**: the difference map shows lighting, focus and hair differences as readily as changes of the mark. It is labelled as a visual aid and measures nothing.

## Ethical considerations

- Automatic outlines are opt-in per person, off by default, labelled experimental, and enter the record only when the person confirms them. A rejection is kept, so the evaluation can count it.
- The descriptive-language check in CI keeps disease names, risk vocabulary and medical prompts out of every user-facing text.
- All processing runs on the household's server. No photo, label or result is sent to a third party.
