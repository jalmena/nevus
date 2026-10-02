# Model card: the neVus analyzers

neVus measures and documents skin marks; it never classifies them. Every analyzer here outputs a description of a photograph: a warning about the photo, a scale, an outline or an alignment. None outputs a diagnosis, a risk or a recommendation, and none is a learned model. Releases up to 0.4.0 use classical computer vision only, so there is no training data and nothing is downloaded.

Each result is stored as an append-only analysis record with the analyzer's name, version, parameters and the hash of its input. A newer version adds records and never overwrites old ones (`nevus reanalyze`). Measurements keep the identifier of the analysis that produced them.

| Analyzer | Version | Runs | Output | Decision |
| --- | --- | --- | --- | --- |
| `quality` | 1.0.0 | every photo | warnings: blurry, too dark, overexposed, glare, low resolution | automatic: a warning, never a refusal |
| `scale.card` | 1.0.0 | every photo of a visit | the reference card's homography to millimetres, tilt, scale uncertainty | automatic: a scale the person can replace |
| `fit` | 1.0.0 | when the person taps | a proposed circle or outline around the tap | the person adjusts and saves |
| `segment.auto` | 1.0.0 | only with the experimental analysis on | an outline without a tap, a proposed size, framing hints | **experimental**: pending until the person confirms or rejects it |
| `align` | 1.0.0 | when the person compares two photos | the transform from one photo to the other, or a refusal with a reason | a visual aid; nothing is recorded as a measurement |
| `candidates` | 1.0.0 | on full-body session photos, only with the experimental analysis on | spots that may be marks, each matched to a confirmed mark of the previous session, new, or uncertain | **experimental**: pending until the person confirms, links or rejects each one |
| `constellation` | 1.0.0 | when a session photographs a region again | the transform from the previous session's photo of the region to the new one, from the pattern of the spots, or a refusal with a reason | a visual aid for the proposals above; nothing is recorded as a measurement |
| `descriptors` | 1.0.0 | when a measurement is saved | the outline's perimeter, compactness and ratio of diameters; the colour of the mark and of the skin around it in CIELAB, their contrast, the mark's lightness spread | automatic, descriptive: stored with the measurement the person confirmed |

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

## `candidates` 1.0.0 (experimental)

- **Method**, on one region's photo from a full-body session:
  1. Hairs are painted over as for `segment.auto`.
  2. The skin is the largest region whose colour is within 24 ΔE of the median colour of the frame's centre (the protocol puts the region there), with thin gaps closed and mark-sized holes filled, so no fixed skin-colour threshold is needed on any tone and the background does not matter. Larger holes (a ruler, a card, a dressing lying on the skin) stay out, so their dark parts cannot become candidates.
  3. Within it, a spot is a compact region darker than its local surroundings (a wide median) by at least 12 lightness units, with a diameter between 0.6 % and 6 % of the photo's short side and a compactness of at least 0.45. At most 80 spots are proposed, the most contrasted first.
- **Matching** with the previous session that photographed the same region: the earlier photo is lined up with the new one by `constellation` (below) or, when either photo has too few spots for a pattern, by `align` restricted to the skin of both photos. Both abstain when unsure. Each mark confirmed then is carried to where it lands:
  - a spot within 2 % of the short side is proposed as that mark (`matched`);
  - when there is none, the mark is proposed where it should be, so the person can look (`uncertain`);
  - spots left over are proposed as `new`;
  - without an alignment, spots are proposed with no suggestion at all.
- **Gates in CI** on synthetic region photos with skin texture, five round spots and eight hairs across the frame, at six steps of the Monk Skin Tone scale (MST 1, 3, 5, 6, 8 and 10):
  - at least four of the five spots are found on every tone, and at most one other proposal is made. Over five seeds per tone the measured recall and precision were both 1.00;
  - two marks confirmed in one session are found again in the next after the region is re-photographed with a shift and a 3° rotation, and a spot that was not there before is proposed as new; a region with thirty spots is lined up by their pattern.
- **Measured on real photographs** (`tools/evaluation/longitudinal_backs.py`, not part of CI because it downloads 23 MB): the 36 CC-BY back photos of 17 persons in the ISIC Archive's collection 217 (UPMC Hillman Cancer Center), taken 168 to 2 639 days apart with different cameras, backgrounds, framing and light. The detector found 10 to 80 spots per photo, on a photo so dark that the first version of the skin mask found no skin too. See `constellation` for the matching results.
- **Limits**: synthetic gates are not a clinical validation. In real photos, expect:
  - false proposals from clothing, jewellery, shadows in skin folds, tattoo ink and freckles, all of which the person rejects; on the real backs above, the cap of 80 was reached on heavily freckled skin, so the faintest spots there are not proposed;
  - missed marks when they are not darker than the skin, sit across a fold, or are very small in a wide photo;
  - fewer matches when the pose, the distance or the light differs a lot between sessions, because the alignment then abstains.
  A `new` proposal says only that no confirmed mark was there in the previous photo; it says nothing about the spot itself.

## `constellation` 1.0.0

- **Method**: the pattern of the spots, which moves with the skin and lasts for years, lines up two sessions the way star fields are matched (Groth 1986; Valdes et al. 1995; Beroiz et al. 2020). Each spot and its four nearest neighbours form triangles whose shape (two ratios of side lengths) is the same whatever the photo's position, rotation or zoom. Triangles of the same shape in both photos vote for a similarity transform; the best are refitted on the spots they pair, as a homography once eight or more pair, with spots of too different a size never paired. A transform is accepted only if it passes three tests: a-contrario (Moisan and Stival 2004), the expected number of chance alignments as good, given how densely the skin is spotted, is below 0.01; it pairs at least 40 % of the spots both photos show; and the paired spots keep their order of darkness (Spearman ≥ 0.3). A second transform about as convincing but elsewhere means the pattern repeats, and the analyzer abstains (`ambiguous_pattern`).
- **Gates in CI**: a synthetic pattern of 40 spots re-photographed with a turn of 8°, a zoom of 1.1, a slight tilt, a fifth of the spots missing and eight new ones is lined up within 1 % of the short side, with at least 80 % of the surviving spots paired and 95 % of the pairs right; 30 pairs of unrelated patterns are all refused; patterns of five spots are refused as too few; photos of different resolutions compare.
- **Measured on real photographs** (the longitudinal backs above): 12 of the 19 consecutive pairs of the same person were lined up, with 10 to 61 spots paired per pair, and all 12 are right on inspection of the overlays and of the paired spots at full resolution. The 7 refusals are photos with ten to twenty detected spots, or a changed pose. Of the 1 216 pairs of photos of **different** persons, **none** was lined up. For comparison, image features (`align`) lined up none of the 19 same-person pairs: between sessions the background and the light change more than the skin does. Each alignment takes under 0.1 s.
- **Limits**: a region with fewer than eight clear spots cannot be lined up this way, and skin features take over only when they agree strongly. The transform is one homography, so it is right over the flat part of a region and drifts where the body curves away or the pose changed; the 2 % matching radius absorbs part of that, and uncertain proposals exist for the rest. Nothing about a mark is inferred from the pairing: it only says where to look.

## `descriptors` 1.0.0

- **Method**: from the outline the person confirmed, the perimeter in millimetres (through the same scale as the sizes), the compactness `4πA/P²` (1 for a circle, less for anything else) and the ratio of the two diameters. From the photograph, the colour of the mark (the outline eroded by the border uncertainty) and of the skin around it (a ring half a radius wide, kept clear of the outline and of the card's print) as means in CIELAB, their difference ΔE (CIE76) and the standard deviation of the mark's lightness. When the reference card is in the photo, its grey patch, printed to read as sRGB `#777777`, sets the exposure and the white balance before the conversion, and the record says `card_grey`; otherwise the values are what the camera saw and say `camera`.
- **Measured** in CI: the 5 mm disc in the card's window measures a compactness above 0.9, a perimeter within 0.9 mm of `5π` and a diameter ratio above 0.9; its lightness is well below the surrounding skin's and the contrast is above 15 ΔE; measurements saved before the descriptors existed are described the same way by `nevus reanalyze --analyzer descriptors`.
- **Limits**: the colour numbers depend on the light, the camera's processing and JPEG compression; the grey patch removes exposure and white-balance drift but is a printed patch, not a calibrated target, so values are comparable between visits of the same card and phone rather than absolute. Compactness depends on how the outline was drawn. None of these numbers has a threshold or an interpretation in neVus; they describe, and the model card's intended use applies to them as to everything else.

## Ethical considerations

- Automatic outlines and spot proposals are opt-in per person, off by default, labelled experimental, and enter the record only when the person confirms them. A rejection is kept, so the evaluation can count it.
- Every region of a full-body session can be skipped, and the regions that may include intimate areas say so before the photo is taken.
- The descriptive-language check in CI keeps disease names, risk vocabulary and medical prompts out of every user-facing text.
- All processing runs on the household's server. No photo, label or result is sent to a third party.
