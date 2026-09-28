# Body map

The body map is where a person places a mark and where the app shows which marks are due. It has to be tappable on a phone, readable at a glance, neutral about who the person is, and stable over time so that stored locations keep their meaning.

## What it is

- **Two views**, front and back, on a 216 × 404 grid inherited from MoleMapper so that the ported zone polygons keep their coordinates. Both views share one silhouette: a body seen from behind is the mirror image of the same outline.
- **56 zones** (28 per view) with MoleMapper's identifiers and names. Names are written from the patient's point of view: on the front view the patient's right is on the left of the screen, on the back view it is on the right. The `side` field is therefore taken from the name, never from the identifier's last digit, which only encodes the screen side. Five head-detail zones (`31xx`) are kept in the ported data for the detail views planned later; they have no silhouette yet and are not served.
- **A location** is a zone code plus a point normalised to the view box (`x`, `y` in 0..1) and the map version (`nevus-body-map/1`). A later map can reinterpret stored points; nothing needs migrating when the artwork changes.

## How it is drawn

The silhouette is a flat, gender-neutral pictogram: a skeleton of tapered capsules (head, neck, trunk polygon, arms, hands, legs, feet) unioned and rounded with a morphological closing, then simplified. It is built by `tools/bodymap/build.py`, so proportions are numbers, not brush strokes, and a change is a diff.

The zone regions are MoleMapper's hit polygons clipped to that silhouette. Where the polygons leave a sliver of the figure uncovered, the sliver goes to the neighbouring zone with the longest shared edge; trunk polygons win where they overlap limbs. The builder asserts that the zones tile the silhouette exactly with no overlaps. Zone boundaries are the straight cuts of the original polygons, which read as the "inner lines" of an anatomical chart.

Previews with zone codes: [front](bodymap/front.svg), [back](bodymap/back.svg).

## Interaction

- Zones are SVG paths exposed as buttons: focusable, named in the account language, `aria-pressed` when selected, activated by tap, Enter or Space.
- A tap inside a zone yields the tapped point (converted through the SVG's screen matrix); the keyboard places at the zone's anchor point, which is guaranteed to lie inside the zone.
- Markers are dots at normalised positions; a due mark uses the attention colour, never red. Clustering of overlapping markers and pinch-zoom are planned for the core-tracking release.

## Attribution

Zone identifiers, names and hit polygons: MoleMapper, Oregon Health & Science University, BSD 3-Clause (full text in `THIRD_PARTY_NOTICES.md`). Silhouette and zone geometry: the neVus project, AGPL-3.0-only.
