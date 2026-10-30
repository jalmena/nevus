"""body map 4: hands and feet as one sees one's own

Revision ID: b4c8e2f19d07
Revises: a7d3f1c2e9b4
Create Date: 2026-10-30 19:00:00.000000

Map 4 redraws the hands and puts the backs of the hands and the tops of the feet in the upper row, the left
one on the left, so thumbs and big toes changed side in most zones; and it lays the head out like an unfolded cube
with the head seen from below added under the face, so the head's pictograms moved and shrank. A mark stored on an
earlier map keeps its place on the body: its point is carried from the old zone's box to the new one, mirrored
where the thumb or the big toe changed side, and its map version becomes 4. On front and back the arms now hang
from the ends of the shoulders: a mark on an arm, a shoulder or a hand moves with it, as does one on the back's
feet, of which only the heels show now. Then a mark on a limb takes the band (thigh, knee, wrist...) its point lies
in on map 4; on the back, the buttocks reach down to where the legs part.
"""

from __future__ import annotations

import re
from itertools import pairwise

import sqlalchemy as sa
from alembic import op

revision: str = "b4c8e2f19d07"
down_revision: str | None = "a7d3f1c2e9b4"
branch_labels = None
depends_on = None

OLD, NEW = "nevus-body-map/3", "nevus-body-map/4"
WIDTH, HEIGHT = 216.0, 404.0
Box = tuple[float, float, float, float]

# Zone: (its box on maps 2 and 3, its box on map 4, whether the drawing was mirrored), in view-box units. The head
# view came with map 2 and did not change until 4; the hands and feet came with map 3.
MOVED: dict[str, tuple[Box, Box, bool]] = {
    "3150": ((2.0, 137.0, 63.0, 219.0), (61.3, 174.0, 104.0, 231.4), False),  # Left Profile
    "3151": ((153.0, 137.0, 214.0, 219.0), (172.0, 174.0, 214.7, 231.4), False),  # Right Profile
    "3170": ((74.0, 36.0, 142.0, 115.0), (114.2, 108.3, 161.8, 163.6), False),  # Top of Head, its ears aside
    "3171": ((68.0, 135.0, 148.0, 221.0), (110.0, 172.6, 166.0, 232.8), False),  # Face: Front
    "3172": ((75.0, 259.0, 141.0, 359.0), (5.2, 174.0, 51.4, 231.4), False),  # Occipital, its ears aside
    "3210": ((22.6, 65.0, 77.0, 139.0), (121.9, 242.0, 198.1, 328.0), True),  # Right Palm
    "3211": ((139.0, 65.0, 193.4, 139.0), (17.9, 242.0, 94.1, 328.0), True),  # Left Palm
    "3220": ((139.0, 245.0, 193.4, 319.0), (121.9, 62.0, 198.1, 148.0), True),  # Back of Right Hand
    "3221": ((22.6, 245.0, 77.0, 319.0), (17.9, 62.0, 94.1, 148.0), True),  # Back of Left Hand
    "3310": ((141.5, 248.5, 175.5, 332.0), (140.0, 241.2, 180.0, 338.8), False),  # Sole of Right Foot
    "3311": ((40.5, 248.5, 74.5, 332.0), (36.0, 241.2, 76.0, 338.8), False),  # Sole of Left Foot
    "3320": ((40.5, 63.5, 74.5, 147.0), (140.0, 56.2, 180.0, 153.8), True),  # Top of Right Foot
    "3321": ((141.5, 63.5, 175.5, 147.0), (36.0, 56.2, 76.0, 153.8), True),  # Top of Left Foot
    # On front and back, map 4 hangs the arms from the ends of the shoulders, so the hands moved out and shrank, and
    # the back shows only the heels of feet that point away. The hands there are only sketched, and short.
    "1850": ((12.5, 188.2, 42.0, 240.4), (14.3, 185.1, 33.9, 212.8), False),  # Right Hand
    "1851": ((174.0, 188.2, 203.5, 240.5), (182.1, 185.1, 201.7, 212.7), False),  # Left Hand
    "2850": ((12.5, 188.2, 42.0, 240.4), (14.3, 185.1, 33.9, 212.8), False),  # Left Hand
    "2851": ((174.0, 188.2, 203.5, 240.5), (182.1, 185.1, 201.7, 212.7), False),  # Right Hand
    "2600": ((70.0, 357.1, 92.8, 400.0), (76.6, 357.1, 93.4, 370.3), False),  # Left Ankle & Foot
    "2601": ((123.2, 357.1, 146.0, 400.0), (122.6, 357.1, 139.4, 370.3), False),  # Right Ankle & Foot
}

# The arms moved out with the hands. A mark on an arm or a shoulder keeps its place on it: at each height, its
# distance from the body's middle is stretched piece by piece between the same landmarks on maps 3 and 4. On the
# arm, those are the arm's inner edge, its axis and its outer edge; above the arm, the shoulder's outline. The neck
# stays put. Each landmark is a distance from the middle at a height, in view-box units.
NECK = 24.0
ARM_3 = ((35.5, 88.0, 11.0), (58.0, 150.0, 8.5), (75.0, 198.0, 6.5))  # axis and radius: shoulder, elbow, wrist
ARM_4 = ((48.0, 88.0, 10.0), (68.0, 150.0, 8.5), (84.0, 198.0, 6.5))
SHOULDER_3 = ((63.5, 24.0), (68.5, 38.0), (77.0, 45.5), (88.0, 46.5))  # height and outline, above the arm
SHOULDER_4 = ((63.5, 24.0), (68.5, 41.0), (77.0, 51.5), (88.0, 58.0))
ARMS = {
    *("1650", "1700", "1750", "1800", "1651", "1701", "1751", "1801"),
    *("2650", "2700", "2750", "2800", "2651", "2701", "2751", "2801"),
}


# Map 4 also cuts the limbs into bands a person can name (thigh, knee, shin or calf, ankle; forearm, wrist, and on
# the back the elbow, forearm and wrist), and moves the lines between neighbouring zones: the abdomen reaches down to
# the navel, the pubic area is new, the buttocks reach down to where the legs part, the chest and the back reach up
# to the arm's edge, and the armpits are new. A mark in one of these families keeps its point and takes the zone of
# the family its point now lies in.
FAMILIES: tuple[tuple[str, ...], ...] = (
    ("1300", "1350", "1360", "1400", "1450", "1500", "1550"),
    ("1301", "1351", "1360", "1401", "1451", "1501", "1551"),
    ("2300", "2350", "2400", "2450", "2500", "2550"),
    ("2301", "2351", "2401", "2451", "2501", "2551"),
    ("1250", "1650", "1660", "1700", "1750", "1800"),
    ("1251", "1651", "1661", "1701", "1751", "1801"),
    ("2250", "2650", "2700", "2750", "2780", "2800"),
    ("2251", "2651", "2701", "2751", "2781", "2801"),
)
NEW_BACK_FOREARMS = {"2780": "2750", "2781": "2751"}  # back to the elbow they were part of, on a downgrade


def _rings(path: str) -> list[list[tuple[float, float]]]:
    """The closed rings of a zone's SVG path ("M x,y x,y ... Z", one per ring)."""
    rings = []
    for part in re.findall(r"M([^MZ]+)Z", path):
        points = [tuple(float(v) for v in pair.split(",")) for pair in part.split()]
        rings.append([(x, y) for x, y in points])
    return rings


def inside(x: float, y: float, rings: list[list[tuple[float, float]]]) -> bool:
    """Even-odd ray casting over every ring, so holes count."""
    hit = False
    for ring in rings:
        for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1], strict=True):
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                hit = not hit
    return hit


def band(code: str, x: float, y: float, zones: dict[str, list[list[tuple[float, float]]]]) -> str:
    """The zone of its family a normalised point lies in on map 4, or the code it had when it lies in none."""
    family = next((members for members in FAMILIES if code in members), None)
    if family is None:
        return code
    px, py = x * WIDTH, y * HEIGHT
    return next((other for other in family if other in zones and inside(px, py, zones[other])), code)


def carry(x: float, y: float, source: Box, target: Box, mirrored: bool) -> tuple[float, float]:
    """A normalised point carried from one zone box to another, mirrored left to right if asked."""
    u = (x * WIDTH - source[0]) / (source[2] - source[0])
    v = (y * HEIGHT - source[1]) / (source[3] - source[1])
    if mirrored:
        u = 1 - u
    nx = (target[0] + u * (target[2] - target[0])) / WIDTH
    ny = (target[1] + v * (target[3] - target[1])) / HEIGHT
    return round(min(1.0, max(0.0, nx)), 4), round(min(1.0, max(0.0, ny)), 4)


def _between(points: tuple[tuple[float, float], ...], at: float) -> float:
    """The value at `at` on a polyline of (position, value) points, held at its ends."""
    if at <= points[0][0]:
        return points[0][1]
    for (a, va), (b, vb) in pairwise(points):
        if at <= b:
            return va + (vb - va) * (at - a) / (b - a)
    return points[-1][1]


def _landmarks(
    arm: tuple[tuple[float, float, float], ...], shoulder: tuple[tuple[float, float], ...], y: float
) -> tuple[float, ...]:
    """The landmarks across the body at height y, as distances from the middle: the neck, then the arm's inner
    edge, axis and outer edge where the arm is, or the shoulder's outline above it."""
    if y < arm[0][1]:
        return (NECK, _between(shoulder, y))
    axis = _between(tuple((h, d) for d, h, _r in arm), y)
    radius = _between(tuple((h, r) for _d, h, r in arm), y)
    return (NECK, axis - radius, axis, axis + radius)


def along_arm(x: float, y: float, forward: bool) -> tuple[float, float]:
    """A normalised point on an arm or a shoulder carried from map 3 to map 4 (or back), keeping its place on it."""
    middle = WIDTH / 2
    px, py = x * WIDTH, y * HEIGHT
    source = _landmarks(ARM_3, SHOULDER_3, py)
    target = _landmarks(ARM_4, SHOULDER_4, py)
    if not forward:
        source, target = target, source
    distance = abs(px - middle)
    if distance > source[0]:
        # Within the piece between two landmarks, or past the last one by as much as it moved.
        index = next((i for i in range(1, len(source)) if distance <= source[i]), len(source) - 1)
        a, b, ta, tb = source[index - 1], source[index], target[index - 1], target[index]
        distance = ta + (distance - a) * (tb - ta) / (b - a) if distance <= b else distance + tb - b
    nx = (middle + (distance if px >= middle else -distance)) / WIDTH
    return round(min(1.0, max(0.0, nx)), 4), y


def _arms(forward: bool) -> None:
    bind = op.get_bind()
    lesions = sa.table(
        "lesions",
        sa.column("id"),
        sa.column("zone_code", sa.String),
        sa.column("x", sa.Float),
        sa.column("y", sa.Float),
        sa.column("body_map_version", sa.String),
    )
    before, after = (OLD, NEW) if forward else (NEW, OLD)
    rows = bind.execute(
        sa.select(lesions.c.id, lesions.c.x, lesions.c.y).where(
            lesions.c.zone_code.in_(sorted(ARMS)),
            lesions.c.body_map_version != after if forward else lesions.c.body_map_version == before,
        )
    ).all()
    for row in rows:
        x, y = along_arm(row.x, row.y, forward)
        bind.execute(sa.update(lesions).where(lesions.c.id == row.id).values(x=x, y=y, body_map_version=after))


def _move(forward: bool) -> None:
    bind = op.get_bind()
    lesions = sa.table(
        "lesions",
        sa.column("id"),
        sa.column("zone_code", sa.String),
        sa.column("x", sa.Float),
        sa.column("y", sa.Float),
        sa.column("body_map_version", sa.String),
    )
    before, after = (OLD, NEW) if forward else (NEW, OLD)
    rows = bind.execute(
        sa.select(lesions.c.id, lesions.c.zone_code, lesions.c.x, lesions.c.y).where(
            lesions.c.zone_code.in_(list(MOVED)),
            lesions.c.body_map_version != after if forward else lesions.c.body_map_version == before,
        )
    ).all()
    for row in rows:
        old_box, new_box, mirrored = MOVED[row.zone_code]
        source, target = (old_box, new_box) if forward else (new_box, old_box)
        x, y = carry(row.x, row.y, source, target, mirrored)
        bind.execute(sa.update(lesions).where(lesions.c.id == row.id).values(x=x, y=y, body_map_version=after))


def _bands(forward: bool) -> None:
    bind = op.get_bind()
    lesions = sa.table(
        "lesions",
        sa.column("id"),
        sa.column("zone_code", sa.String),
        sa.column("x", sa.Float),
        sa.column("y", sa.Float),
        sa.column("body_map_version", sa.String),
    )
    codes = sorted({code for members in FAMILIES for code in members})
    rows = bind.execute(
        sa.select(lesions.c.id, lesions.c.zone_code, lesions.c.x, lesions.c.y).where(lesions.c.zone_code.in_(codes))
    ).all()
    if forward:
        from nevus.bodymap import body_map

        zones = {zone.code: _rings(zone.path) for zone in body_map().zones}
        for row in rows:
            code = band(row.zone_code, row.x, row.y, zones)
            if code != row.zone_code:
                bind.execute(sa.update(lesions).where(lesions.c.id == row.id).values(zone_code=code))
    else:
        for row in rows:
            if row.zone_code in NEW_BACK_FOREARMS:
                bind.execute(
                    sa.update(lesions).where(lesions.c.id == row.id).values(zone_code=NEW_BACK_FOREARMS[row.zone_code])
                )


def upgrade() -> None:
    _move(forward=True)
    _arms(forward=True)
    _bands(forward=True)


def downgrade() -> None:
    _bands(forward=False)
    _arms(forward=False)
    _move(forward=False)
