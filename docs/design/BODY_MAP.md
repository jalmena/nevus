# Body map

The body map is where a person places a mark and where the app shows which marks are due. It has to be tappable on a phone, readable at a glance, neutral about who the person is, and stable over time so that stored locations keep their meaning.

## What it is

- **Two views**, front and back, on a 216 × 404 grid inherited from MoleMapper so that the ported zone polygons keep their coordinates. Both views share one silhouette, a body seen from behind being the mirror image of the same outline, with two differences: the back has no armpit to unroll, so there the gap between each arm and the trunk climbs, along the arm's edge, to the line where the arm leaves the shoulder; and the feet point away, so under each ankle the back shows only the heel. The arms hang from the ends of the shoulders (map 4), and the crotch rises to the height where the cleft of the buttocks ends: in front as a round, behind as the notch between the two round lobes of the buttocks, which meet the thighs at the fold.
- **57 zones** (28 MoleMapper zones per view, and the pubic area on the front) with MoleMapper's identifiers and names. Names are written from the patient's point of view: on the front view the patient's right is on the left of the screen, on the back view it is on the right. The `side` field is therefore taken from the name, never from the identifier's last digit, which only encodes the screen side. Five head-detail zones (`31xx`) are kept in the ported data for the detail views planned later; they have no silhouette yet and are not served.
- **Three detail views** (map 2 and later): the head, unfolded like a cube (the top above the face, the profiles at its sides, the head seen from below under the chin, added in map 4, and the back of the head under that; six zones); the hands and the feet (map 3, redrawn in map 4), each in two rows as a person looks at their own, the left one on the left of the screen. The upper row is the backs of the hands (thumbs inward) and the tops of the feet, tinted darker, with a round hole where the ankle stands; the lower row is the palms (thumbs outward) and the soles. No caption is needed. The hand is drawn open and a little wider than in a photo, as the skin of the hand unrolled onto the page: palm and back together cover all of it, the palm taking in the edge below the little finger.
- **Landmarks** (map 4) are drawn over the zones, each only where it belongs, and take no tap: nipples and navel on the front, the cleft of the buttocks on the back, eyes, nostrils, mouth and ears on the head, nails on the backs of the hands and the tops of the feet.
- **A person's anatomy**, chosen part by part in the person's profile so that any body can be drawn (chest: breasts or unset; genitals: vulva, penis and testicles, or unset), adds thin lines to the front: the lower curve of each breast, centred on the nipple; the cleft of the vulva; the penis springing from the top of a scrotum shaped by the two testicles. The words are anatomical, never man or woman; the silhouette is the same for every body, and unset draws none of it.
- **Limbs in bands a person can name** (map 4): the front leg is thigh, knee, shin and ankle, the back leg thigh, back of the knee, calf and ankle; the arm is forearm and wrist in front, elbow, forearm (new codes `2780`/`2781`) and wrist behind. Marks stored before map 4 take the band their point lies in. The armpits (`1660`/`1661`) sit on the front between the line where the arm leaves the shoulder and the top of the armpit's curve; the shoulder is the cap above that line, and the chest or the back reaches up to the arm's edge. The abdomen, and behind it the lower back, reaches down to the navel's height. On the back the buttocks reach down to the groin, beside the crotch's round. The hands on front and back are drawn small and short: they are only sketched there.
- **Anatomy zones** (`1260`/`1261` breasts, `1370` penis, `1371` scrotum) lie over the zones under them and exist only for a person whose profile sets the part; removing a part with marks on it asks first, and the marks keep their place and their zone.
- **The pubic area** (map 4, code `1360`) is a zone of its own on the front, between the legs, carved out of the pelvis and the tops of the thighs; it is not one of MoleMapper's zones.
- **Front and back sketch the head, the hands and the feet**, veiled and not markable: a tap there opens the detail view. Marks placed there before map 4 still show where they were put.
- **A location** is a zone code plus a point normalised to the view box (`x`, `y` in 0..1) and the map version (`nevus-body-map/4` today). A later map can reinterpret stored points; map 4 moved the hands and feet, so the migration `body_map_4` carries their stored points from the old zone box to the new one, mirrored where the thumb or the big toe changed side; points on the arms and shoulders, which moved out, are stretched at each height between the same landmarks on both maps (the neck, the arm's edges and axis, the shoulder's outline).

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
