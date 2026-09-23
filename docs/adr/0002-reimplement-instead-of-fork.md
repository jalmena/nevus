# ADR-0002: Reimplement neVus instead of forking MoleMapper

- Status: Accepted
- Date: 2026-09-23
- Deciders: engineering (architect); starting point set by the Product Owner

## Context

The Product Owner asked to start from `ohsu-molemapper/MoleMapper_Final`, the public source release of the MoleMapper iOS research app (OHSU, BSD licence), and to determine whether to fork it, fork and progressively rewrite it, reuse selected components, use it only as a reference, or reimplement the concept.

The [audit](../audits/MOLEMAPPER_AUDIT.md) found an abandoned, iOS-only code dump: one commit (2024), no README, tags or tests; Swift 4.2/5.0 and Objective-C on UIKit, Core Data and AVFoundation with a 72 MB binary of OpenCV 3.2; a BSD-3 licence whose repository copy has a defective clause 3 while the per-file headers are correct and reserve all trademarks; third-party assets under separate licences (Freepik, Pexels); bundled OHSU, Sage and ResearchKit logos; a committed analytics API key; and a measurement pipeline that works on a screen-sized preview with US coins only and no notion of uncertainty. Nothing in the codebase can run in a browser or in Python, which is where a self-hosted, CasaOS-packaged web application lives.

The valuable parts are data and ideas: the 61-zone body taxonomy, the 32 zone polygons defined in code, the coin diameter table, the tap-seeded auto-fit measurement interaction, the alignment pins shown during re-capture, the per-lesion history view and the reminders.

## Decision

neVus is a clean reimplementation inspired by MoleMapper (option D), taking selected components under option C:

- port the zone taxonomy and zone polygons as data (JSON and generated SVG regions);
- port the coin table, extended with Euro coins and other references;
- reimplement the tap-seeded auto-fit algorithm in Python following the original structure, rescaled to full-resolution images and extended with an uncertainty estimate;
- use MoleMapper's screen flow as a functional specification, not as code.

Nothing else is taken: no UIKit or Core Data code, no artwork, no logos, no names, no onboarding text, no consent or study material, no research back-end integration.

## Consequences

- `THIRD_PARTY_NOTICES.md` reproduces the OHSU BSD-3 notice verbatim (the per-file header form, which is the correct one, alongside the repository licence file) and lists every ported component and where it lives.
- The project states "inspired by MoleMapper (OHSU)" and disclaims affiliation and endorsement; the MoleMapper and War on Melanoma marks are never used.
- Body-map artwork is redrawn as SVG (licence-clean sources such as MakeHuman renders), never copied from the raster PNGs whose rights are not explicit.
- neVus must design from day one what MoleMapper lacked: measurement on full-resolution images, uncertainty, tilt and perspective handling through a planar reference marker, non-US references, export and backup, multi-user self-hosting, a quality gate and versioned analysis records.
- The BSD-3 terms are compatible with neVus's AGPL-3.0-only licence; the ported components remain BSD-attributed inside an AGPL work.
