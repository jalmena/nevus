# SPDX-License-Identifier: AGPL-3.0-only
"""The design tokens reports use, mirrored from frontend/src/design-system/tokens/tokens.css (light theme).

Printed pages use the light theme on white paper; the brand block keeps its dark paper. A test checks
these values against the token file, so the app and its reports cannot drift apart.
"""

from __future__ import annotations

COLOURS: dict[str, str] = {
    "surface": "#fffcf7",
    "surface-2": "#efe8de",
    "border": "#d9d1c5",
    "ink": "#2b2a28",
    "ink-2": "#5e5a54",
    "ink-3": "#706a63",
    "accent": "#1f6f6b",
    "attention": "#b9791b",
    "on-attention": "#1b1a19",
    "marker": "#2b2a28",
    "marker-selected": "#1f6f6b",
    "chart-1": "#0b9488",
    "brand-paper": "#17161a",
    "brand-ink": "#ede8e0",
    "brand-accent": "#5fb3ae",
}
