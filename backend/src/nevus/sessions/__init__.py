# SPDX-License-Identifier: AGPL-3.0-only
"""Full-body sessions (FR-SES-01): one photo per region of the body, in a standard order and pose.

The protocol is data: each capture zone names the body map zones it covers, so a mark found on a zone
photo can be linked to the registry. Every zone can be skipped; those marked sensitive say so in the
interface. Names and pose instructions live in the interface's catalogues, keyed by the zone id.
"""

from __future__ import annotations

from dataclasses import dataclass

PROTOCOL_VERSION = "nevus-session-protocol/1"


@dataclass(frozen=True)
class CaptureZone:
    id: str
    covers: tuple[str, ...]
    sensitive: bool = False


PROTOCOL: tuple[CaptureZone, ...] = (
    CaptureZone("face", ("1100", "3150", "3151", "3171")),
    CaptureZone("scalp", ("2100", "3170", "3172")),
    CaptureZone("chest", ("1200", "1250", "1251", "1650", "1651")),
    CaptureZone("abdomen", ("1300", "1301", "1350", "1351"), sensitive=True),
    CaptureZone("upper-back", ("2200", "2250", "2251", "2650", "2651")),
    CaptureZone("lower-back", ("2300", "2301", "2350", "2351"), sensitive=True),
    CaptureZone("right-arm-front", ("1700", "1750", "1800")),
    CaptureZone("left-arm-front", ("1701", "1751", "1801")),
    CaptureZone("right-arm-back", ("2701", "2751", "2801")),
    CaptureZone("left-arm-back", ("2700", "2750", "2800")),
    CaptureZone("palms", ("1850", "1851", "3210", "3211")),
    CaptureZone("backs-of-hands", ("2850", "2851", "3220", "3221")),
    CaptureZone("right-leg-front", ("1400", "1450", "1500", "1550")),
    CaptureZone("left-leg-front", ("1401", "1451", "1501", "1551")),
    CaptureZone("right-leg-back", ("2401", "2451", "2501", "2551")),
    CaptureZone("left-leg-back", ("2400", "2450", "2500", "2550")),
    CaptureZone("tops-of-feet", ("1600", "1601", "3320", "3321")),
    CaptureZone("soles", ("2600", "2601", "3310", "3311")),
)

BY_ID = {zone.id: zone for zone in PROTOCOL}
