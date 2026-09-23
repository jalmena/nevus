# Landscape: longitudinal mole and skin-lesion tracking

Date: 2026-09-23. Purpose: find what neVus can actually reuse or learn from existing projects, products, datasets and research, and where the regulatory line sits for a self-hosted, non-diagnostic tracker.

Evidence legend:

- **[V]** verified this session against a primary source (a LICENSE file; the GitHub, ISIC, Synapse, figshare, iTunes or NCBI APIs; an official page; a paper's full text or abstract).
- **[R]** reported by secondary sources (search snippets, vendor marketing, news), not independently checked.
- **[I]** inference or recommendation.

Nothing here is legal advice.

## Top-line findings

1. Commercially usable data exists for the non-diagnostic tasks, but only a few sets qualify: iToBoS 2024 (CC BY 4.0, 59,997 lesion boxes on 16,954 skin-region tiles), SLICE-3D Permissive (CC-BY/CC-0, 217,477 lesion crops), ISIC 2016–2018 segmentation sets (CC-0), PAD-UFES-20 (CC BY 4.0, smartphone photos), the MSKCC Skin Tone set (CC-BY, balanced across Fitzpatrick I–VI) and the UPMC longitudinal back photos (CC-BY). Most well-known sets are non-commercial or research-only; DermNet explicitly bans AI training. [V]
2. The best reusable code is OpenDerm's `skinmap` (MIT, July 2026): cross-scan registration and per-mole size change measured against a detector noise estimate. MoleMapper (BSD) is a good reference for UX and coin measurement. The Skin3D repository contains no tracking code, only annotations under CC BY-NC-SA; the JHU tracking code is also CC BY-NC-SA. [V]
3. No open, permissively licensed dermatology image-quality model exists. TrueImage, ImageQX and Legit.Health's work are closed. [V]
4. The EU regulatory line is explicit (Borderline Manual 2019, §9.7 vs §9.8): an app that only stores mole pictures and shows them to a doctor is not a device; an app that compares images and assesses moles is. FDA guidance draws the same line. Automated measurement and change flags are the gray zone. [V/I]
5. Engagement evidence is sobering: MoleMapper reports that habit formation was "almost non-existent" and monthly prompts were insufficient; a randomised trial of a self-monitoring app with monthly reminders showed no benefit. [V]

## A. Projects and products

### A1. MoleMapper (OHSU / Sage Bionetworks / Apple / Dan Webster)

- An iPhone ResearchKit app plus an observational study, first released in October 2015; OHSU took over development and research oversight in June 2016. [V]
- The iOS app "Mole Mapper Melanoma Study" is at v3.4.0, last updated 2022-12-28; release notes say the study no longer recruits but the app can still be used. Data collection ran June 2016 to December 2022. No successor project found. [V]
- 2017 paper: Webster et al., *Scientific Data* 4:170005, <https://www.nature.com/articles/sdata20175>. 2,069 participants, 3,274 mole measurements, 2,422 curated images, mean mole size 3.95 mm. Measurement: mole mm = reference mm × mole px / reference px; US coins by default, any known-length object accepted. Body map with 59 zones; pin on the zone photo, then a close-up with adjustable circle overlays. [V]
- 2017 data: Synapse `syn5576734` (<https://doi.org/10.7303/syn5576734>), tables `syn6829807`–`syn6829811`. Access is ACT-managed with conditions of use: no re-identification, keep confidential, use only as described in an intended-use statement, no commercial advertising or participant re-contact, publish open access, acknowledge participants. [V]
- 2025 release: Petrie, Samatham, Webster, Leachman, *Scientific Data* (2 Aug 2025), <https://doi.org/10.1038/s41597-025-05552-1>. 27,499 mole crops, 7,305 skin-patch crops, 1,000 zone images, 4,158 participants (iOS 2.x/3.x and Android 1.x); about 12 % of moles measured more than once; unlabelled, no masks; not enriched for Fitzpatrick IV+. Data: Synapse `syn51520810` (<https://doi.org/10.7303/syn51520810>), Certified User plus a use statement and an agreement "confirming you will not publish or share the data". [V]
- Key lesson (Synapse wiki, verbatim): "habit formation for an activity with no direct rewards and a frequency measured in months not hours or days was almost non-existent. Simple monthly prompting also proved insufficient." [V]
- Code: <https://github.com/ohsu-molemapper/MoleMapper_Final> (Swift/ObjC, BSD-style licence, © 2015 OHSU; see the [audit](../audits/MOLEMAPPER_AUDIT.md)); Android port <https://github.com/ResearchStack/MoleMapperAndroid> (Apache-2.0, last push 2019). "MoleMapper" is an OHSU trademark. [V]
- Reusable: the UX flow (photograph the zone, tap moles, adjust circles, use a coin), the zone taxonomy, the tap-seeded measurement algorithm (BSD), and the 2025 images for internal evaluation only, under the data-use agreement. Not reusable: the name, the raster artwork quality, any redistribution of the data or derived artefacts. [I]

### A2. MoleCare (all candidates trace to one UK company)

1. App "MoleCare – Skin Health Tracker" by MoleCare LTD (London): iOS since 2019-08-19, v2.4.7 dated 2026-03-04. Features: front/back body map, reminders, side-by-side history, PDF reports for clinicians, UV index, premium AI chat; disclaimer "does NOT provide medical diagnosis". Website <https://molecare.co.uk/> ("Track moles. Spot changes. Walk in prepared."). Listed in the NHS App Library [R]. [V unless marked]
2. GitHub organisation <https://github.com/MoleCare> (all repos Apache-2.0): `molecare-ml`, a Flask/TensorFlow Xception melanoma classifier trained on ISIC dermoscopy (only accuracy measured, Fitzpatrick performance "unmeasured"), whose `/evolution` service turns ABCDE deltas into "risk impact" and "concern level" — exactly the output neVus must avoid; its detection uses LAB colour space, Otsu on L and an adaptive threshold. Also `molecare-desktop` (Electron shell with `safeStorage` tokens and a CSP), `molecare-mcp`, `molecare-skin-llm`, `privacy-gate-llm`. [V]
3. A Flippa sale listing (<https://flippa.com/10869387-molecare>, seller "2AY Ltd", about 10k installs). [R]

No academic paper or other project called MoleCare was found. Reusable: the "walk in prepared" report framing and the Electron hardening pattern. Not reusable: the classifier and the evolution risk scoring.

### A3. Skin3D (SFU Medical Image Analysis Lab)

- Paper: Zhao, Kawahara, Abhishek, Shamanian, Hamarneh, *Medical Image Analysis* 77:102329 (2022), <https://doi.org/10.1016/j.media.2021.102329>, arXiv <https://arxiv.org/abs/2105.00374>. Faster R-CNN on the unwrapped texture image, lesions mapped back to 3D, graph matching using anatomical correspondences and geodesic distances. 88 % matching accuracy on prominent lesion pairs; 71 % "longitudinal" accuracy once detection errors are included ("longitudinal" means two poses of the same subject, not visits separated in time). [V]
- Repository <https://github.com/jeremykawahara/skin3d>: LICENSE is CC BY-NC-SA 4.0, last push 2025-08-31. It contains only 25,000+ bounding-box CSVs (train/val/multi-annotator test plus lesion IDs linking the two scans), loaders and visualisation. No detector and no matching code. [V]
- Underlying data: 3DBodyTex.v1 (<https://cvi2.uni.lu/3dbodytexv1/>), 400 scans of 200 subjects; the licence agreement must be signed by the recipient and the institution's research administration office director, which makes it practically unavailable for a home project. [V/I]
- Related: JHU MICCAI 2023 code <https://github.com/weilunhuang-jhu/LesionCorrespondenceTBP3D> (CC BY-NC-SA 4.0); JHU tracking dataset repo <https://github.com/weilunhuang-jhu/LesionTrackingDatasetTBP3D> (no licence file); DermSynth3D <https://github.com/sfu-mial/DermSynth3D> (LICENSE file AGPL-3.0; README badge says GPL). [V]
- Reusable: the matching idea (anatomical landmarks + inter-lesion geometry + graph assignment), reimplemented from the paper. Not reusable: the data or code in a commercial setting; 3D scanning in general.

### A4. OpenDerm

The only real candidate is OpenDerm, open-source robotic 3D skin imaging by Marion Lepert (reported as a Stanford robotics PhD student) [R]; repository created 2026-07-27 [V].

- Links: <https://openderm.github.io/> and <https://github.com/MarionLepert/openderm>. Software MIT (API-verified), hardware CERN-OHL-P-2.0. Hardware: 4-axis gantry, Canon R7 with 100 mm macro lens, cross-polarised ring flash, two laser distance sensors; 78 px/mm; about $8,500 in parts. No peer-reviewed paper found. [V]
- Reusable MIT code, verified by reading the source: `src/skinmap/lesions.py` (melanin-channel flat-fielding via −log R and mole thresholding; a haemoglobin channel for angiomas), `compare_scans.py` (CLAHE-SIFT + FLANN + RANSAC similarity alignment that abstains below a minimum inlier count and falls back to matching the mole constellation), `track_moles.py` (per-mole area, perimeter and solidity change with a `detector_sigma` noise estimate). Tuned for 78 px/mm cross-polarised macro images, so it needs re-tuning for smartphone photos. [V/I]

### A5. ISIC Archive

- API v2 (<https://api.isic-archive.com/api/v2/>): public images need no authentication; 553,019 images on 2026-09-23. Useful endpoints: `/images/`, `/images/facets/?query=image_type:"clinical: close-up"`, `?collections=<id>`, `/collections/`. Every image carries its own `copyright_license` plus metadata such as `anatom_site_1..5`, `fitzpatrick_skin_type`, `clin_size_long_diam_mm`, `patient_id`, `lesion_id`, `acquisition_day`. CLI: <https://github.com/ImageMarkup/isic-cli> (Apache-2.0). [V]
- Composition (API facets) [V]: dermoscopic 124,961; clinical close-up 9,316; clinical overview 432; TBP tile close-up 401,059; TBP tile overview 16,990. Licences: CC-BY 258,980; CC-BY-NC 245,288; CC-0 48,751.
- Challenge datasets (<https://challenge.isic-archive.com/data/>) [V]: 2016 CC-0; 2017 CC-0 (2,000 training images with masks); 2018 Task 1–2 CC-0 (2,594 training images with masks plus validation and test); 2018 Task 3 (HAM10000/MSK) CC-BY-NC; 2019 (25,331) CC-BY-NC; 2020 (33,126) CC-BY-NC; 2024 SLICE-3D CC-BY-NC (401,059) with "SLICE-3D Permissive" (217,477 images, CC BY 4.0, <https://doi.org/10.34970/2024-slice-3d-permissive>; in the archive CC-BY 188,812 plus CC-0 28,665); MILK10k CC-BY-NC.
- SLICE-3D: Kurtansky et al., *Scientific Data* 2024, <https://doi.org/10.1038/s41597-024-03743-w>. 401,059 crops from 1,042 patients at seven centres; 15×15 mm field of view, about 133×133 px, "comparable in optical resolution to smartphone images"; crops exported for auto-detected lesions over 2.5 mm plus all manually tagged; metadata includes clinical size, area, eccentricity, LAB colour, border and asymmetry metrics, 3D position. Skin tone is not documented. [V]
- Collections relevant to neVus (`https://api.isic-archive.com/collections/<id>/`) [V]:

  | ID | Collection | Images | Image type | Licence | Notes |
  | --- | --- | --- | --- | --- | --- |
  | 459 | iToBoS 2024 | 16,954 | TBP overview tiles | CC-BY | |
  | 217 | UPMC longitudinal posterior trunks | 36 | 4500×3000 px | CC-BY | `acquisition_day` (0, 1400, …) and `patient_id` |
  | 413 | MSKCC Skin Tone Labeling | 4,879 | 3,678 dermoscopic + 1,201 clinical close-up | CC-BY | Fitzpatrick I–VI roughly 750–950 each |
  | 406 | PAD-UFES-20 | 2,298 | clinical close-up | CC-BY | |
  | 251 | HIBA 2019–2022 | 1,616 | incl. 340 clinical overview | CC-BY | |
  | 328 | Repeated Dermoscopic Images | 585 | dermoscopic | CC-BY-NC | five sequential images of each lesion in one session |
  | 485 | MEL-SELF | 3,008 | dermoscopic | CC-BY | |
  | 425 | MILK10k | 5,240 + 5,240 | paired clinical close-up and dermoscopic | CC-BY-NC | |

- Usable for non-diagnostic models: yes. The licences are copyright licences; CC-0/CC-BY images can be used for segmentation, detection and quality models, commercial use included, with attribution; diagnosis labels can be ignored. NC images are acceptable only for a strictly personal, non-commercial deployment and block any distribution. [I]
- Resolution note: iToBoS tiles are about 12 px/mm and SLICE-3D crops about 9 px/mm; they resemble zone/full-body photos rather than close-ups. [I]

### A6. Other open-source projects with a real codebase

| Project | Licence | Last push | Stack / what it does | Relevance |
| --- | --- | --- | --- | --- |
| <https://github.com/TDK250/track-a-mole> | GPL-3.0 [V] | 2026-03 | Next.js, Three.js 3D body, Dexie, Capacitor; local-first; AES-GCM encrypted `.tam` backups; "Nth day of month" reminders | UX reference; its 3D models ship encrypted (`*.glb.enc`), so the assets are not reusable |
| <https://github.com/come97/mole-tracker> | none (all rights reserved) [V] | 2026-05 | React 19 + Vite PWA + Supabase; each photo encrypted client-side with AES-GCM-256, key derived from a 6-digit PIN via PBKDF2-SHA256 (250k iterations) | Pattern reference for end-to-end encrypted photo storage |
| <https://github.com/houssam-marzak/mole_monitor_automation> | MIT [V] | 2026-04 | n8n + Telegram + Grounding DINO (prompt "metal coin . dark skin mole .") + JS calibration from a 20-cent Euro coin; Google Sheets storage | Zero-shot coin + mole idea; cloud dependencies conflict with privacy-first |
| <https://github.com/mattbroadbridge/MoleTrack> | none [V] | 2023 | Python desktop app: body outline + photo log | Trivial |
| <https://github.com/benjaminalbert/SCIDOG> | GPL-3.0 [V] | 2021 | Java; SCIDOG segmentation for non-dermoscopic images (IEEE Access 2020) | Algorithm reference |
| <https://github.com/Francesco182g/Naevus> | Apache-2.0, archived [V] | 2022 | Django + Angular AR lesion visualisation | Low value |
| <https://github.com/lumo-imaging/total-body-photography-dicom> | none [V] | 2024 | Python DICOM builders for wide-field regional images, dermoscopy, 3D meshes | Export format reference |
| <https://github.com/fastenhealth/fasten-onprem> | GPL-3.0 [V] | 2026-02 | Self-hosted personal/family health record | Possible sibling in a self-hosted stack |

UMSkinCheck (University of Michigan, 2012) offered a 23-photo guided full-body baseline, push-pins on a body illustration, reminders and a risk calculator [R]; it no longer appears in App Store searches and never had public code. Searches for DermTrack, SkinTrack, moletrack and "mole monitor" found only empty or unrelated repositories; no Home Assistant integration for skin tracking exists. [V]

### A7. Commercial apps (UX reference only)

- **Miiskin** (Denmark): the iOS app is now "Miiskin: Rx Dermatology Visits" (v1.135.1, 2026-09-09), pivoted to US teledermatology [V]. "Automatic Skin Imaging" with the phone standing on a table while CV/AR guides the poses; AI skin mapping flags new marks; side-by-side comparisons; coin-based "Mole Sizing"; PIN/Face ID and blurring of private areas in full-body photos; states it does not diagnose [R]. Takeaways: automatic full-body capture, new-mark flags, privacy blur.
- **SkinVision** (Netherlands): low/high risk indication from photos; EU MDR Class IIa certification, 5 Aug 2025 [V]. Its risk indication is exactly the feature that turns an app into a regulated device. [I]
- **MoleScope / DermEngine** (MetaOptima): smartphone dermoscope plus cloud platform with total body photography, "MoleMatching", "Evolution Tracker", Visual Search [R]; FDA-registered, CE-marked, TGA-listed, ISO 13485 [V]. Takeaway: a dedicated pairing/matching view; avoid the hardware dependency and clinical decision support.
- **FotoFinder ATBM master / Bodystudio** (Germany): automated total body mapping in under three minutes with cross-polarised RAW images; "Bodyscan" flags new and changed lesions during capture; a 2024 *European Journal of Cancer* study reports 92.9 % (baseline) and 96.7 % (follow-up) detection of clinically relevant melanocytic lesions; Moleanalyzer pro AI score; MDR Class IIa via TÜV SÜD (2023) [R]. Takeaway: standardised poses and automatic new/changed markers; avoid the AI score.
- **Canfield VECTRA WB360 + DermaGraphix**: 92 cameras build a 3D avatar; DermaGraphix Tracker flags new and changed lesions; capture templates guide poses [R]. SLICE-3D and iToBoS show its export format: 15 mm crops plus size and colour metrics [V]. Takeaway: navigation on a body avatar and lesion IDs with standard crops.
- **DermaSensor**: handheld elastic-scattering spectroscopy for primary care; FDA De Novo, January 2024 [R]. No UX value; it illustrates that "adjunctive diagnosis" means a Class II authorisation.
- Precedent: in 2015 the FTC acted against MelApp and Mole Detective over melanoma-risk claims (<https://www.ftc.gov/news-events/news/press-releases/2015/02/ftc-cracks-down-marketers-melanoma-detection-apps>). [R]

## B. Datasets

| Dataset | Size / image type | Licence / access | Skin tone | Use for neVus |
| --- | --- | --- | --- | --- |
| ISIC 2018 Task 1 | 2,594 training images with binary masks (+ validation/test); dermoscopic | CC-0 [V] | not labelled | Segmentation pretraining (expect dermoscopy → phone domain shift) |
| PH2 (<https://www.fc.up.pt/addi/ph2%20database.html>) | 200 dermoscopic, 768×560, with masks | Research/education only; redistribution and commercial use not allowed [V] | not labelled | Internal evaluation only |
| HAM10000 (<https://doi.org/10.7910/DVN/DBW86T>) | 10,015 dermoscopic (+ lesion masks) | CC BY-NC 4.0 [V/R] | not labelled | Non-commercial only |
| BCN20000 | 18,946 dermoscopic | ISIC lists CC-BY-NC [V]; the paper's "CC BY 4.0" is likely the article licence [I] | not labelled | Non-commercial only |
| PAD-UFES-20 (<https://data.mendeley.com/datasets/zr7vgbcyr2/1>) | 2,298 smartphone clinical images; 1,373 patients; metadata incl. diameter and Fitzpatrick type | CC BY 4.0 [V] | FST I 153 / II 876 / III 392 / IV 62 / V 10 / VI 1 [V] | Quality and segmentation evaluation; own masks needed |
| Derm7pt (<https://github.com/jeremykawahara/derm7pt>) | 1,011 cases, paired clinical + dermoscopic | Repo CC BY-NC-SA 4.0 [V]; images from a dermoscopy atlas, registration needed [R] | not labelled | Clinical↔dermoscopic pairs; non-commercial only |
| Fitzpatrick17k (<https://github.com/mattgroh/fitzpatrick17k>) | 16,577 clinical atlas images, 114 conditions | CC BY-NC-SA 3.0; many image URLs broken; request form [V] | FST labelled | Fairness research only; few moles |
| DDI (<https://ddi-dataset.github.io/>) | 656 images, 570 patients, biopsy-proven | Stanford Research Use Agreement: non-commercial research only, no redistribution or derivatives [V] | FST I–VI balanced | Internal fairness evaluation only |
| SD-198 / SD-260 | 6,584 / 20,600 clinical images (from DermQuest) | Unclear [R] | – | Avoid [I] |
| DermNet (<https://dermnetnz.org/image-licence>) | Atlas website | CC BY-NC-ND for watermarked images; clause 25 bans AI training/testing [V] | – | Not usable |
| DermaMNIST (<https://github.com/MedMNIST/MedMNIST>) | HAM10000 downsampled, 28–224 px | CC BY-NC 4.0 [R]; code Apache-2.0 [V] | – | Toy only |
| MoleMapper 2017 / 2025 | Consumer smartphone photos (see A1) | Synapse controlled access; no sharing or publishing [V] | Biased toward light skin [V] | Internal evaluation of consumer-photo quality [I] |
| SLICE-3D / SLICE-3D Permissive | 401,059 / 217,477 TBP crops, about 133 px | CC-BY-NC / CC-BY + CC-0 [V] | Undocumented [V] | Lesion/artefact verifier, re-identification embeddings, weak size labels |
| MIT "ugly duckling" (Soenksen 2021) | 38,283 images incl. 15,244 non-dermoscopic, 133 patients [V] | Data "may be provided for noncommercial research purposes upon reasonable request" [V]; code <https://github.com/lrsoenksen/SPL_UD_DL> AGPL-3.0 [V] | – | Detection-pipeline idea; code compatible with neVus's AGPL |
| 3DBodyTex + Skin3D annotations | 400 3D scans; 25k boxes | Institution-signed agreement [V]; annotations CC BY-NC-SA [V] | Varied [R] | Not practical |
| iToBoS 2024 (<https://figshare.com/articles/dataset/iToBoS_2024_-_Skin_Lesion_Detection_with_3D-TBP/28452545>) | 16,954 tiles of about 7×9 cm; 59,997 boxes (lesions ≥ 2.5 mm); 100 patients; 19.2 GB | CC BY 4.0 [V] | Fitzpatrick I–II only [V] | Train the zone/full-body lesion detector |
| UPMC longitudinal trunks (<https://doi.org/10.34970/630662>) | 36 high-resolution back photos with `acquisition_day` | CC-BY [V] | – | Registration and new-lesion test set |
| MSKCC Skin Tone (<https://doi.org/10.34970/962049>) | 4,879 images (1,201 clinical) + Monk scale, Pantone, colorimeter | CC-BY [V] | Balanced I–VI [V] | Fairness evaluation |
| SCIN (<https://github.com/google-research-datasets/scin>) | 10k+ crowdsourced smartphone images; self-reported and estimated Fitzpatrick type + estimated Monk tone | SCIN Data Use License: reproduce, share, adapt with attribution; no re-identification; no NC clause in the sections read [V partial] | Diverse | Quality gate and skin detection across tones (mostly rashes, not moles) |
| MILK10k (<https://doi.org/10.34970/648456>) | 5,240 lesions, clinical + dermoscopic pairs | CC-BY-NC [V] | – | Non-commercial only |
| MED-NODE (<https://www.cs.rug.nl/~imaging/databases/melanoma_naevi/>) | 170 clinical images | Reported CC BY 4.0 [R] | – | Small test set |
| Dermofit (<https://licensing.edinburgh-innovations.ed.ac.uk/product/dermofit-image-library>) | 1,300 clinical images with masks | Paid academic licence (£75); no commercial use [R] | – | Rare clinical-photo masks, non-commercial only |
| IMA++ (<https://arxiv.org/abs/2512.21472>) | 17,684 masks on 14,967 ISIC images; 2,394 images with 2–5 annotators | Licence unclear [V] | – | Modelling border uncertainty |

## C. Research and algorithms

### C1. Image quality assessment for dermatology photos

- TrueImage (Vodrahalli et al., arXiv 2020, <https://arxiv.org/abs/2010.02086>): ensemble of deep and classical checks with reasons "blur / lighting / other"; rejects about 50 % of poor images while keeping about 80 % of good ones. [R]
- TrueImage 2.0 (<https://arxiv.org/abs/2209.09105>): trained on 1,700 images; AUC 0.78 for poor quality, 0.84 for blur, 0.70 for lighting; in a prospective study of 98 patients it cut the number of patients with a poor-quality image by 68 %. The code is not open (<https://github.com/kailas-v/TrueImage2.0> contains only the clinical-study CSV, no licence). [V]
- ImageQX (Jalaboi et al., <https://arxiv.org/abs/2209.04699>): 36,509 images from the "Imagine" lesion-tracking app (146 countries); labels bad framing, bad lighting, blur, low resolution, distance; a 15 MB EfficientNet-B0; macro-F1 0.73 vs inter-rater 0.77. No code or data release. [V]
- Legit.Health cross-domain IQA (2025, <https://arxiv.org/abs/2506.16116>): trained on natural-image IQA datasets; PLCC 0.836 on dermatology images; code and data withheld. [V]
- Google Derm Foundation (<https://huggingface.co/google/derm-foundation>): 6144-dimensional embeddings; image-quality assessment is a listed downstream use; HAI-DEF terms permit commercial use but not use that would make Google a medical-device "manufacturer". [V]
- Licence traps: IQA-PyTorch (`pyiqa`) is PolyForm Noncommercial [V]. Safer: OpenCV contrib's quality module (Apache-2.0) and idealo NIMA (Apache-2.0). [V]
- Patent: Skinio US 11,854,200 B2 (granted 2023-12-26) claims ML quality scoring with retake prompts, anomaly detection and temporal comparison via point-set registration (<https://patents.google.com/patent/US11854200B2/en>). [V]

### C2. Lesion detection in wide-field and total-body photos

- Soenksen et al., *Science Translational Medicine* 2021 (<https://www.science.org/doi/10.1126/scitranslmed.abb3652>): SIFT/LoG blob detection, then a CNN, then "ugly duckling" ranking; code AGPL; data on request for non-commercial research. [V]
- Birkenfeld et al., CMPB 195:105631 (2020): wide-field images, AUC 0.89. [R]
- Strzelecki et al., *Sensors* 21:6639 (2021, <https://pmc.ncbi.nlm.nih.gov/articles/PMC8513024/>): histogram thresholding sensitivity 0.95 / precision 0.60; template correlation 0.90 / 0.81; YOLOv3 0.94 / 0.94; fused sensitivity 0.95–0.96, precision 0.91–0.94; area error under 10 % for lesions over 3 mm; failure modes: uneven lighting, hair, skin folds, shadows. No code. [V]
- Betz-Stablein et al., *Dermatology* 238(1):4–11 (2022): CNN naevus counts on 3D total body photography, n = 82. [R]
- Ahmedt-Aristizabal et al. (CSIRO), CMPB 232:107451 (2023, <https://arxiv.org/abs/2205.07085>): 3DSkin-mapper camera array, CNN detection and 3D tracking; no code. [V]
- Li, Esteva et al., arXiv 2016 (<https://arxiv.org/abs/1612.01074>): composites lesion crops onto body photos to create training data — a cheap way to synthesise detection data from SLICE-3D crops. [V/I]
- Maguire et al. (UPMC/Veytel), *JID Innovations* 3:100181 (2023, <https://pmc.ncbi.nlm.nih.gov/articles/PMC10030255>): HSI-channel thresholding gives 97.1 % sensitivity for lesions ≥ 2 mm; software proprietary. [V]
- iToBoS dataset paper (<https://www.nature.com/articles/s41597-025-05483-x>); DermSynth3D (*MedIA* 2024, AGPL). [V]

### C3. Longitudinal lesion matching between sessions

- Korotkov et al., IEEE TMI 34:317–338 (2015): 21-camera turntable scanner with mapping and change detection. [V]
- Korotkov et al., IEEE JBHI 23:586–598 (2019, <https://pubmed.ncbi.nlm.nih.gov/30004894/>): non-rigid deformation of region-of-interest coordinate planes plus progressive graph-matching outlier rejection; precision 99.92 %, recall 81.65 %; no code. [V]
- Mirzaalian, Lee, Hamarneh, *MedIA* 27:84–92 (2016): structured graphical models combining geometry and texture. [V]
- Skin3D (2022, see A3). Strąkowska & Kociołek (Springer 2022): feature matching plus triangulation; sensitivity 85.9 %, precision 86.9 %. [R]
- Huang W-L et al. (Johns Hopkins), MICCAI 2023 (<https://arxiv.org/abs/2307.09642>), code CC BY-NC-SA [V]; "Revisiting lesion tracking in 3D TBP" (<https://arxiv.org/abs/2412.07132>, reported in *MedIA* 2026): a 25K-pair dataset over 198 subjects, 89.9 % success at 10 mm. [V/R]
- UPMC 2023 point-pattern registration: coarse scale and rotation, low-resolution translation, tile-level refinement, cross-checks; tolerates 1:3 scale change and ±10° rotation, needs at least 50 % overlap; registered 87/87 image fields. Patent Veytel US 12,380,564 B2 (granted 2025-08-05, <https://patents.google.com/patent/US12380564B2/en>). [V]
- No open code for 2D smartphone-to-smartphone mole matching exists beyond OpenDerm's `compare_scans.py`. Permissive general-purpose matchers: LightGlue (Apache-2.0) with DISK or ALIKED features, RoMa (MIT), XFeat (Apache-2.0), LoFTR (Apache-2.0). Not SuperPoint (non-commercial research only). [V]

### C4. Segmentation on clinical (non-dermoscopic) photos

- Classical: Otsu on L* or Cr, colour k-means, GrabCut, active contours; MoleMapper's tap-seeded adaptive threshold; OpenDerm's melanin-channel threshold. SCIDOG (Albert, IEEE Access 2020, GPL); Jafari et al. 2016 (<https://arxiv.org/abs/1609.02374>). [V/R]
- Promptable models: SAM and SAM 2 (Apache-2.0); MedSAM (Apache-2.0, *Nature Communications* 2024); SAM 3 (Nov 2025) under the custom "SAM License" (commercial use allowed with restrictions); SkinSAM (<https://arxiv.org/abs/2304.13973>, fine-tuned on HAM10000, Dice 0.888, dermoscopic only). [V/R]
- Domain shift and variability: almost all open masks are dermoscopic; openly licensed clinical-photo masks barely exist. Ribeiro 2019 (<https://arxiv.org/abs/1906.02415>) finds a heavy tail of discordant annotations; IMA++ (2025) finds inter-annotator agreement associated with malignancy. Border uncertainty should be shown to the user, not hidden. [V/I]

### C5. Automatic scale estimation with reference objects

- MoleMapper coin formula (see A1). [V]
- Swift HealX (*PLoS One* 2017, <https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0183139>): a 1 cm adhesive marker for scale and colour; ICC 0.97–1.00 vs 0.92–0.97 for a ruler. [R]
- WoundAmbit (ECML PKDD 2025, <https://arxiv.org/abs/2504.06185>): four 12 mm ArUco markers, averaging px/mm over marker pairs to reduce perspective error. [V/R]
- OpenCV ArUco/ChArUco (Apache-2.0): <https://docs.opencv.org/4.13.0/d5/dae/tutorial_aruco_detection.html>.
- Smartphone measurement in Mohs surgery (Vickers, *Skin Res Technol* 2023, <https://pmc.ncbi.nlm.nih.gov/articles/PMC10234163/>): r = 0.93–0.97, most lesions within 25 % or 0.5 cm — far too coarse for moles averaging about 4 mm. [V/I]
- Reiter et al. (MSKCC), *Skin Res Technol* 2022 (<https://pubmed.ncbi.nlm.nih.gov/34455638/>): manual diameter ICC 0.88; automated (3D) vs manual (2D) differ by 1.5 % on average; comparing two time points side by side is far more consistent than counting at each time point (SD 4.65 vs 38.80). [V]
- Error budget [I]: σ_d ≈ √((d·σ_scale)² + (2·σ_border)²). A 4 mm mole with 2 % scale error and ±0.15 mm border uncertainty gives about 0.3 mm; changes under roughly 0.6–0.9 mm are therefore not reliably detectable. Camera tilt foreshortens by cos θ: about 1.5 % at 10° and 6 % at 20°; gate on the marker's pose.

### C6. Change detection between two images of the same lesion

- Navarro, Escudero-Viñolo, Bescós, IEEE JBHI 2019 (<https://pubmed.ncbi.nlm.nih.gov/29993849/>); Zhang et al., IEEE TMI 2021 (<https://pubmed.ncbi.nlm.nih.gov/33180721/>); Yu et al., IEEE TMI 2022 (<https://pubmed.ncbi.nlm.nih.gov/34648437/>) — all dermoscopy. UPMC 2023: registration gave a 1.7-fold increase in detected changes (odds ratio 4.85). [V]
- The only open, permissive code found: OpenDerm's `compare_scans.py` and `track_moles.py` (MIT). ISIC collection 328 (same-session repeats) suits estimating a test-retest noise floor. [V/I]

### C7. Skin-tone bias

- Daneshjou et al., *Science Advances* 2022 (<https://www.science.org/doi/10.1126/sciadv.abq6147>): models lost 27–36 % of ROC-AUC on DDI and did worse on dark skin; fine-tuning on diverse data closed the gap. [V]
- Groh et al., CVPRW 2021: most datasets lack skin-type labels; Fitzpatrick17k addresses this. [V/R]
- Benčević et al., CMPB 245:108044 (2024): a significant correlation between segmentation performance and skin colour, against darker skin; common mitigations were ineffective; code <https://github.com/marinbenc/lesion_segmentation_bias> (no licence). [V]
- Implication: iToBoS is Fitzpatrick I–II only, SLICE-3D undocumented, MoleMapper biased toward light skin. Evaluate per skin tone with the MSKCC set, SCIN and PAD-UFES-20. The Monk Skin Tone scale is open (CC BY; MST-E <https://arxiv.org/abs/2305.09073>). [V/I]

### C8. Regulatory: medical device or not? (not legal advice)

**FDA**

- Device software / mobile apps guidance (<https://www.fda.gov/media/80958/download>): enforcement discretion covers apps that use the camera "for purposes of documenting or transmitting pictures (e.g., photos of a patient's skin lesions or wounds) to supplement or augment what would otherwise be a verbal description in a consultation"; regulatory focus covers "software functions that analyze an image of a skin lesion using mathematical algorithms… and provide the user with an assessment of the risk of the lesion". [V]
- General Wellness guidance, 6 Jan 2026 (<https://www.fda.gov/media/90652/download>): a product is not "general wellness" if its labelling or UI refers to specific diseases or diagnostic thresholds, recommends clinical action, or states an intended use of screening or monitoring a disease; a neutral "evaluation by a healthcare professional may be helpful" note is allowed if it names no disease and does not call the output abnormal. A melanoma-surveillance framing does not fit wellness; the documentation framing is the better fit. [V/I]

**EU**

- MDCG 2019-11 rev.1 (June 2025, <https://health.ec.europa.eu/document/download/b45335c5-1679-4c71-a91c-fc7a4d37f12b_en?filename=mdcg_2019_11_en.pdf>): software that acts on data "beyond storage, archival, communication, simple search, lossless compression" may be medical device software; Rule 11: information used for diagnostic decisions is Class IIa or higher, everything else Class I. [V]
- Borderline Manual, May 2019 edition (<https://health.ec.europa.eu/system/files/2020-08/md_borderline_manual_05_2019_en_0.pdf>): §9.7, an app that takes and stores mole pictures and shows them to a doctor "should not be qualified as standalone medical device software"; §9.8, an app that stores and compares pictures with image-processing assessment and melanoma probability is a device (Class IIa or higher under Rule 11). Version 4 of the manual (Sept 2025) exists; whether it keeps these examples was not verified. [V/I]
- Scope: the MDR applies to devices made available "in the course of a commercial activity, whether in return for payment or free of charge"; the Blue Guide assesses "commercial activity" case by case. A tool built and self-hosted only for oneself is not placed on the market; publishing it as open source is a gray area that depends on context. If neVus ever became a Class IIa+ device, the EU AI Act's high-risk rules would also apply to its ML parts. [R/I]

**Where the line sits** [I]

- Lowest risk: storing and organising photos by body site; reminders; user-driven measurement (a digital ruler); side-by-side and overlay views; clinician reports.
- Gray zone: automatic mm measurement; automatic "changed" or "new lesion" flags.
- Clearly a device: risk or ABCDE scores, melanoma probability, "see a doctor" alerts triggered by the algorithm.
- Patents: before any distribution beyond personal use, run a freedom-to-operate check against the Veytel and Skinio patents.

## D. What neVus can actually reuse or learn (ranked)

1. **OpenDerm `skinmap` (MIT)**: CLAHE-SIFT/RANSAC alignment with abstention, melanin-channel detection and per-mole change with a noise estimate — a ready template for the close-up and zone comparison pipeline.
2. **iToBoS 2024 (CC BY 4.0)** for training the zone/full-body lesion detector; the only large, commercially usable set of lesion boxes. Fitzpatrick I–II and Vectra imagery, so augment and validate on phone photos.
3. **SLICE-3D Permissive (CC-BY/CC-0)** for a lesion-vs-artefact patch verifier, embeddings for re-identifying lesions across sessions, and weak size labels; ignore the malignancy labels.
4. **Printed ArUco/ChArUco card with a colour patch (OpenCV, Apache-2.0), MoleMapper's coin method as fallback**: mm scale, tilt gating and colour normalisation; fiducial markers achieved ICC 0.97–1.00 in wound care.
5. **"Tap the mole" segmentation with SAM 2 / MedSAM (Apache-2.0) plus a classical Otsu/melanin fallback**; measurements stay user-confirmed, which also keeps them on the documentation side of the regulatory line.
6. **Noise-floor evaluation sets**: UPMC longitudinal backs (CC-BY, real time-separated pairs) and ISIC same-session repeat images (NC, internal use) to set the "no detectable change" threshold (roughly 0.6–0.9 mm for a 4 mm mole).
7. **Skin-tone evaluation suite**: MSKCC Skin Tone (CC-BY, balanced I–VI), SCIN (smartphone, Monk tone), PAD-UFES-20 (CC BY 4.0). Segmentation is known to degrade on darker skin.
8. **Matching algorithms to reimplement from papers**: Korotkov 2019 (graph-matching outlier rejection), UPMC 2023 (coarse-to-fine point-pattern registration), Skin3D/JHU (landmarks plus inter-lesion geometry).
9. **Location taxonomy**: DICOM CID 4029 "Dermatology Anatomic Sites" with CID 245 laterality (<https://dicom.nema.org/medical/dicom/Final/cp1674_ft_nyuskinlesionnumbering.pdf>) and the ISIC Delphi 513-term surface anatomy (<https://pubmed.ncbi.nlm.nih.gov/32770737/>); structured, SNOMED-mapped locations make DICOM/FHIR export straightforward.
10. **Licence-clean body-map art**: MakeHuman assets are CC0 and the project claims no rights over exported models (<https://github.com/makehumancommunity/makehuman>), so front/back SVGs can be rendered from them; `react-native-body-highlighter` (MIT) shows the SVG-region pattern.
11. **Quality-gate taxonomy from TrueImage/ImageQX** (blur, lighting, framing, distance, resolution) implemented with classical checks first: Laplacian variance, exposure and glare, marker found, marker tilt. Avoid `pyiqa` (non-commercial).
12. **Permissively licensed ML stack**: RT-DETR, D-FINE, RF-DETR, YOLOX, detectron2 (Apache-2.0); LightGlue with DISK/ALIKED, RoMa or XFeat. Ultralytics (AGPL) is compatible with neVus's AGPL-3.0 licence but adds AGPL obligations to any downstream user; prefer Apache-2.0 detectors.
13. **UX patterns**: Miiskin's phone-on-table guided full-body capture, "new mark" highlights and privacy blur; FotoFinder/Vectra standard pose templates; MoleMapper's zone photo then tap moles; MoleCare's "walk in prepared" PDF report; a swipe/overlay comparison view.
14. **Engagement design**: MoleMapper saw almost no habit formation and the Walter 2020 RCT (<https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2761860>) found monthly reminders did not help; build around appointment-driven workflows ("prepare my dermatology visit"), not streaks or monthly nags.
15. **Regulatory guardrails** from Borderline Manual §9.7 vs §9.8, the FDA device-software guidance and the 2026 wellness guidance: no risk scores or ABCDE scoring; no disease names or thresholds in the UI; no algorithm-triggered medical prompts; comparisons started by the user; a clear "documentation only" intended-use statement. See [ADR-0003](../adr/0003-automatic-analysis-boundary.md).

**Avoid for any distributable product** [V]: Skin3D and JHU code and data (NC-SA); 3DBodyTex; DermNet (bans AI training); DDI (no derivatives); HAM10000, BCN20000, ISIC 2019/2020, SLICE-3D standard, MILK10k, Fitzpatrick17k, Derm7pt, PH2 (non-commercial or research-only); MoleMapper data (no sharing); Soenksen data (non-commercial); SuperPoint and IQA-PyTorch (licence freedom); every diagnosis classifier.

## Key sources

- MoleMapper 2017 paper <https://pmc.ncbi.nlm.nih.gov/articles/PMC5308198/> · 2025 release <https://pmc.ncbi.nlm.nih.gov/articles/PMC12318069/> · Synapse `syn51520810` <https://www.synapse.org/Synapse:syn51520810> · code <https://github.com/ohsu-molemapper/MoleMapper_Final>
- Skin3D <https://github.com/jeremykawahara/skin3d> · OpenDerm <https://openderm.github.io/>, <https://github.com/MarionLepert/openderm>
- ISIC challenge data <https://challenge.isic-archive.com/data/> · SLICE-3D paper <https://pmc.ncbi.nlm.nih.gov/articles/PMC11324883/> · iToBoS <https://figshare.com/articles/dataset/iToBoS_2024_-_Skin_Lesion_Detection_with_3D-TBP/28452545>, <https://www.nature.com/articles/s41597-025-05483-x>
- UPMC/Veytel <https://pmc.ncbi.nlm.nih.gov/articles/PMC10030255> · Soenksen 2021 <https://www.science.org/doi/10.1126/scitranslmed.abb3652> · Revisiting lesion tracking <https://arxiv.org/abs/2412.07132>
- TrueImage 2.0 <https://arxiv.org/abs/2209.09105> · ImageQX <https://arxiv.org/abs/2209.04699> · DDI <https://ddi-dataset.github.io/> · Benčević 2024 <https://doi.org/10.1016/j.cmpb.2024.108044>
- FDA device software guidance <https://www.fda.gov/media/80958/download> · FDA General Wellness 2026 <https://www.fda.gov/media/90652/download> · MDCG 2019-11 rev.1 · EU Borderline Manual 2019 <https://health.ec.europa.eu/system/files/2020-08/md_borderline_manual_05_2019_en_0.pdf>
- Veytel patent <https://patents.google.com/patent/US12380564B2/en> · Skinio patent <https://patents.google.com/patent/US11854200B2/en>
- MoleCare <https://github.com/MoleCare> · SkinVision MDR <https://www.skinvision.com/press-release/skinvision-earns-europes-top-medical-certification-for-ai-powered-skin-cancer-detection> · DermEngine registrations <https://www.dermengine.com/device-registration> · DermNet image licence <https://dermnetnz.org/image-licence> · PAD-UFES-20 <https://data.mendeley.com/datasets/zr7vgbcyr2/1>
