# SPDX-License-Identifier: BSD-3-Clause
"""Zone taxonomy and hit polygons ported from MoleMapper (OHSU).

Copyright (c) 2017-2022 Oregon Health & Science University. Ported from
``ohsu-molemapper/MoleMapper_Final`` at commit 4f3bd8a: the 32 base shapes in
``Source/Common/Helpers/VariableStore.m`` and their placement in
``Source/BodyMapDrawing/BodyFrontView.m``, ``BodyBackView.m`` and
``HeadDetailView.m``; the 61 identifiers and names in
``Source/CoreData/Zone30+CoreDataClass.swift``. The full BSD 3-Clause licence
text is reproduced in THIRD_PARTY_NOTICES.md at the repository root.

Coordinates are points on MoleMapper's 216 x 404 drawing grid, kept verbatim.
The ``view``, ``side`` and ``region`` fields are additions for neVus: the last
digit of a MoleMapper identifier encodes the screen side, not the anatomical
side, and the names are written from the patient's point of view.
"""

from __future__ import annotations

GRID = (216.0, 404.0)

# Base shape id -> list of (x, y) vertices, first vertex = moveTo, path closed implicitly.
BASE_SHAPES: dict[int, list[tuple[float, float]]] = {
    10: [(50.0, 50.0), (0.0, 50.0), (0.0, 0.0), (50.0, 0.0)],
    15: [(0.0, 43.0), (42.0, 43.0), (42.0, 0.0), (0.0, 0.0)],
    17: [(35.5, 0.0), (0.0, 0.0), (0.0, 43.0), (35.5, 43.0)],
    40: [(45.5, 35.0), (0.0, 35.0), (0.0, 0.0), (45.5, 0.0)],
    45: [(40.0, 44.0), (0.0, 44.0), (0.0, 0.0), (40.0, 0.0)],
    50: [(35.0, 30.5), (0.0, 30.5), (0.0, 0.0), (35.0, 0.0)],
    55: [(31.0, 28.0), (0.0, 28.0), (0.0, 0.0), (31.0, 0.0)],
    60: [(34.0, 0.0), (0.0, 0.0), (0.0, 45.0), (34.0, 45.0)],
    300: [(0.0, 4.46094), (0.0, 39.0), (37.0, 39.0), (37.0, 0.0), (0.80664, 0.0)],
    301: [(37.0, 4.46094), (37.0, 39.0), (0.0, 39.0), (0.0, 0.0), (36.1934, 0.0)],
    650: [
        (29.8516, 21.9092),
        (26.0254, 45.6953),
        (0.0, 35.2754),
        (9.80566, 10.2275),
        (43.2168, 0.0),
        (45.2188, 0.0),
        (47.6611, 14.6387),
    ],
    651: [
        (17.8096, 21.9092),
        (21.6357, 45.6953),
        (47.6611, 35.2754),
        (37.8555, 10.2275),
        (4.44434, 0.0),
        (2.44238, 0.0),
        (0.0, 14.6387),
    ],
    700: [(28.7383, 46.6055), (31.0684, 40.4463), (36.7207, 9.23047), (13.6592, 0.0), (0.0, 35.7324)],
    701: [(7.98242, 46.6055), (5.65234, 40.4463), (0.0, 9.23047), (23.0605, 0.0), (36.7207, 35.7324)],
    750: [(28.7383, 36.6104), (0.0, 25.7363), (9.73633, 0.0), (38.4746, 10.873)],
    751: [(9.73633, 36.6104), (38.4746, 25.7363), (28.7383, 0.0), (0.0, 10.873)],
    800: [(28.7383, 36.7227), (0.0, 25.8486), (10.0498, 0.0), (38.7881, 10.874)],
    801: [(10.0498, 36.7227), (38.7881, 25.8486), (28.7383, 0.0), (0.0, 10.874)],
    850: [(46.9912, 30.457), (35.1543, 61.7393), (0.0, 48.4395), (0.0, 31.2852), (11.8389, 0.0), (46.9922, 13.3018)],
    851: [(0.0, 30.457), (11.8379, 61.7393), (46.9922, 48.4395), (46.9912, 31.2852), (35.1533, 0.0), (0.0, 13.3018)],
    1200: [
        (2.00195, 9.65234),
        (10.5547, 60.915),
        (18.5625, 60.915),
        (27.1152, 9.65234),
        (29.1172, 9.65234),
        (29.1172, 0.0),
        (0.0, 0.0),
        (0.0, 9.65234),
    ],
    1250: [
        (0.0, 55.5898),
        (36.1934, 55.5898),
        (36.1934, 36.624),
        (32.1895, 36.624),
        (26.0781, 0.0),
        (8.26953, 7.27051),
    ],
    1251: [(36.1934, 55.5898), (0.0, 55.5898), (0.0, 36.624), (4.00391, 36.624), (10.1133, 0.0), (27.9238, 7.27051)],
    1350: [(44.5, 49.8569), (0.0, 33.2471), (7.5, 0.0), (44.5, 0.0)],
    1351: [(0.0, 49.8569), (44.5, 33.2471), (37.0, 0.0), (0.0, 0.0)],
    1400: [(46.5, 16.6279), (46.5, 51.2539), (0.0, 51.2539), (0.0, 0.0), (2.0, 0.0)],
    1401: [(0.0, 16.6279), (0.0, 51.2539), (46.5, 51.2539), (46.5, 0.0), (44.5, 0.0)],
    2200: [
        (24.6729, 24.291),
        (27.1162, 9.65234),
        (29.1182, 9.65234),
        (29.1172, 0.0),
        (0.0, 0.0),
        (0.00098, 9.65234),
        (2.00293, 9.65234),
        (4.44434, 24.291),
    ],
    2250: [(36.1934, 0.0), (26.0791, 0.0), (8.26953, 7.27051), (0.0, 55.5898), (36.1934, 55.5898)],
    2251: [(0.0, 0.0), (10.1133, 0.0), (27.9238, 7.27051), (36.1934, 55.5898), (0.0, 55.5898)],
    2350: [(8.5, 0.0), (45.5, 0.0), (45.5, 49.5), (0.0, 49.5), (0.0, 31.7139)],
    2351: [(37.0, 0.0), (0.0, 0.0), (0.0, 49.5), (45.5, 49.5), (45.5, 31.7139)],
}

# (code, view, origin x, origin y, MoleMapper name, base shape id)
PLACEMENTS: list[tuple[str, str, float, float, str, int]] = [
    ("1100", "front", 83.0, 1.22705, "Head", 10),
    ("1200", "front", 93.4414, 51.2275, "Neck & Center Chest", 1200),
    ("1250", "front", 71.8076, 75.5186, "Right Pectoral", 1250),
    ("1251", "front", 108.0, 75.5186, "Left Pectoral", 1251),
    ("1300", "front", 71.0, 131.1084, "Right Abdomen", 300),
    ("1301", "front", 108.0, 131.1084, "Left Abdomen", 301),
    ("1350", "front", 63.499, 170.1084, "Right Pelvis", 1350),
    ("1351", "front", 108.0, 170.1084, "Left Pelvis", 1351),
    ("1400", "front", 61.5, 203.3555, "Right Upper Thigh", 1400),
    ("1401", "front", 108.0, 203.3555, "Left Upper Thigh", 1401),
    ("1450", "front", 65.5, 254.6094, "Right Lower Thigh & Knee", 45),
    ("1451", "front", 110.5, 254.6094, "Left Lower Thigh & Knee", 45),
    ("1500", "front", 66.5, 298.6094, "Right Upper Calf", 50),
    ("1501", "front", 114.5, 298.6094, "Left Upper Calf", 50),
    ("1550", "front", 69.5, 329.1094, "Right Lower Calf", 55),
    ("1551", "front", 115.5, 329.1094, "Left Lower Calf", 55),
    ("1600", "front", 65.0, 357.1094, "Right Ankle & Foot", 60),
    ("1601", "front", 117.0, 357.1094, "Left Ankle & Foot", 60),
    ("1650", "front", 50.2246, 60.8799, "Right Shoulder", 650),
    ("1651", "front", 118.1143, 60.8799, "Left Shoulder", 651),
    ("1700", "front", 39.5293, 97.3447, "Right Upper Arm", 700),
    ("1701", "front", 139.75, 97.3447, "Left Upper Arm", 701),
    ("1750", "front", 29.793, 133.0771, "Right Upper Forearm", 750),
    ("1751", "front", 147.7324, 133.0771, "Left Upper Forearm", 751),
    ("1800", "front", 19.7432, 158.8135, "Right Lower Forearm", 800),
    ("1801", "front", 157.4688, 158.8135, "Left Lower Forearm", 801),
    ("1850", "front", 1.48926, 182.2344, "Right Hand", 850),
    ("1851", "front", 167.5186, 182.2344, "Left Hand", 851),
    ("2100", "back", 83.0, 1.22705, "Head", 10),
    ("2200", "back", 93.4414, 51.2275, "Neck", 2200),
    ("2250", "back", 71.8076, 75.5186, "Left Upper Back", 2250),
    ("2251", "back", 108.001, 75.5186, "Right Upper Back", 2251),
    ("2300", "back", 71.0, 131.1084, "Left Lower Back", 300),
    ("2301", "back", 108.0, 131.1084, "Right Lower Back", 301),
    ("2350", "back", 62.501, 170.1094, "Left Glute", 2350),
    ("2351", "back", 108.001, 170.1094, "Right Glute", 2351),
    ("2400", "back", 62.501, 219.6094, "Left Upper Thigh", 40),
    ("2401", "back", 108.001, 219.6094, "Right Upper Thigh", 40),
    ("2450", "back", 65.5, 254.6094, "Left Lower Thigh & Knee", 45),
    ("2451", "back", 110.5, 254.6094, "Right Lower Thigh & Knee", 45),
    ("2500", "back", 66.5, 298.6094, "Left Upper Calf", 50),
    ("2501", "back", 114.5, 298.6094, "Right Upper Calf", 50),
    ("2550", "back", 69.5, 329.1094, "Left Lower Calf", 55),
    ("2551", "back", 115.5, 329.1094, "Right Lower Calf", 55),
    ("2600", "back", 65.0, 357.1094, "Left Ankle & Foot", 60),
    ("2601", "back", 117.0, 357.1094, "Right Ankle & Foot", 60),
    ("2650", "back", 50.2246, 60.8799, "Left Shoulder", 650),
    ("2651", "back", 118.1143, 60.8799, "Right Shoulder", 651),
    ("2700", "back", 39.5293, 97.3447, "Left Upper Arm", 700),
    ("2701", "back", 139.75, 97.3447, "Right Upper Arm", 701),
    ("2750", "back", 29.793, 133.0771, "Left Elbow", 750),
    ("2751", "back", 147.7324, 133.0771, "Right Elbow", 751),
    ("2800", "back", 19.7432, 158.8135, "Left Lower Forearm", 800),
    ("2801", "back", 157.4688, 158.8135, "Right Lower Forearm", 801),
    ("2850", "back", 1.48926, 182.2344, "Left Hand", 850),
    ("2851", "back", 167.5186, 182.2344, "Right Hand", 851),
    # Head detail view: kept for the detail views planned in later releases; no silhouette yet.
    ("3150", "head", 43.25, 102.5, "Face: Left Side", 15),
    ("3151", "head", 130.75, 102.5, "Face: Right Side", 15),
    ("3170", "head", 90.25, 54.5, "Top of Head", 17),
    ("3171", "head", 90.25, 102.5, "Face: Front", 17),
    ("3172", "head", 90.25, 150.5, "Back of Head", 17),
]


def side_of(code: str, view: str, name: str) -> str:
    """Anatomical side from the patient's point of view, taken from the name rather than the id digit."""
    if name.startswith("Right"):
        return "right"
    if name.startswith("Left"):
        return "left"
    if "Left" in name:
        return "left"
    if "Right" in name:
        return "right"
    return "midline"


def region_of(code: str) -> str:
    n = int(code)
    if n in (1100, 2100) or n >= 3000:
        return "head"
    hundreds = n % 1000
    if hundreds < 400:
        return "trunk"
    if hundreds < 650:
        return "leg"
    return "arm"


def absolute_polygon(code: str) -> list[tuple[float, float]]:
    """The zone's hit polygon in grid coordinates (base shape translated to its origin)."""
    for c, _view, ox, oy, _name, shape in PLACEMENTS:
        if c == code:
            return [(round(ox + x, 4), round(oy + y, 4)) for x, y in BASE_SHAPES[shape]]
    raise KeyError(code)
