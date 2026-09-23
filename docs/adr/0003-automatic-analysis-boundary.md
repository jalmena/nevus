# ADR-0003: Automatic analysis is opt-in, off by default, experimental and user-confirmed

- Status: Accepted
- Date: 2026-09-23
- Deciders: Product Owner, on the architect's recommendation

## Context

The brief wants automatic image analysis as a differentiator: quality checks, segmentation and measurement, alignment and change detection between observations, and eventually matching of full-body sessions with "potential new lesion" candidates that the user confirms or rejects. It also states that neVus is not a diagnostic tool and that no automated result may be presented as a diagnosis.

Regulation draws its line close to those features (this record is not legal advice):

- The European Commission's Borderline Manual (May 2019 edition) uses mole apps as worked examples. §9.7: an app that takes and stores pictures of moles and shows them to a doctor is not standalone medical-device software. §9.8: an app that stores and compares pictures, with image processing that assesses the moles and gives a melanoma probability, is a medical device, which under MDR 2017/745 Rule 11 means Class IIa or higher, a notified body, a quality system, clinical evaluation and post-market surveillance.
- MDCG 2019-11 rev. 1 (2025) qualifies software that does more with data than storage, archival, communication, simple search or lossless compression as potential medical-device software when the intended purpose is medical.
- The FDA's device-software guidance applies enforcement discretion to apps that document or transmit pictures of skin lesions to supplement a consultation, and regulates software that analyses a lesion image with algorithms and provides a risk assessment. The FDA General Wellness guidance (January 2026) excludes anything that names a disease or diagnostic thresholds.
- The MDR applies to devices made available in the course of a commercial activity, whether paid or free. A tool a person builds and self-hosts for their own household is not placed on the market; publishing it as open source is a gray area that depends on context and on how the intended purpose is presented.

Within the brief's scope, the safe side holds registration, photos by body site, reminders, user-driven and user-confirmed measurement, user-initiated side-by-side and overlay comparison, and reports for a clinician. The gray zone holds automatic measurement in mm and automatic "this lesion changed" or "possible new lesion" flags. Risk scores, ABCDE scores, malignancy classifiers and algorithm-triggered "see a doctor" prompts are clearly on the device side and are excluded by the brief itself.

## Decision

1. neVus declares its intended use as a personal documentation and measurement aid that does not diagnose, screen for or assess the risk of any disease. The statement appears in the README, the product requirements, the in-app about screen and every generated report.
2. By default neVus behaves like the §9.7 example: it stores, organises, measures with user confirmation, compares on the user's request and reports.
3. Automatic analyses (segmentation-based measurement without a user seed, change flags between observations, lesion detection on zone photos, session-to-session matching and new-lesion candidates) are gated behind a per-profile setting that is **off by default**. When enabled they are labelled "experimental" everywhere they appear, every result must be explicitly confirmed or rejected by the user before it becomes part of the record, and no result ever triggers advice, alerts or prompts about health.
4. neVus never ships a malignancy classifier, a risk score, an ABCDE score or a melanoma probability, not even behind the experimental setting.
5. A lint in continuous integration checks user-facing copy and report templates against a list of disease names, risk words and diagnostic thresholds, so the language stays descriptive: sizes, dates, differences and uncertainties.
6. Every automatic result is stored as a versioned analysis record (analyzer name, version, model hash, parameters, inputs) alongside the user's decision, so the record shows what was suggested, by which code, and what the person decided.

## Consequences

- Product requirements and the roadmap carry the boundary: Phases 5 and 6 (computer vision, full-body sessions) are built and shipped behind the experimental setting; the first releases are fully useful without it.
- The intended-use statement and the descriptive-language lint constrain UI copy, documentation and marketing text; the sarcastic tone of the README must not drift into medical claims.
- Should neVus ever be distributed commercially or bundled by a third party, a fresh regulatory assessment and a freedom-to-operate check against known patents on lesion registration and photo quality scoring are required; this record does not remove that need.
- Users who want the automatic features accept one extra step (enabling them per profile) and see the "experimental" label; that friction is the point.
