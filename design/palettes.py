"""Curated color palettes shared by every generator.

Each palette has a background, an "ink" (primary text/line) color, and a
short list of accent colors for secondary shapes. Keeping palettes small
and curated (instead of randomizing hues) is what keeps generated art
looking intentional instead of like a random-color-picker demo.
"""
from __future__ import annotations

PALETTES: dict[str, dict] = {
    "terracotta_boho": {
        "bg": "#F3E4D3",
        "ink": "#7A3B2E",
        "accent": ["#C97C5D", "#9CAF88", "#E7B75F"],
    },
    "sage_minimal": {
        "bg": "#F5F5F0",
        "ink": "#3E4A3D",
        "accent": ["#8A9A83", "#C9C2A6", "#5B6E5B"],
    },
    "midnight_gold": {
        "bg": "#1B1B2F",
        "ink": "#F4E9D8",
        "accent": ["#C9A227", "#8C7853", "#EDE6D6"],
    },
    "blush_neutral": {
        "bg": "#FBEFEA",
        "ink": "#5C4033",
        "accent": ["#E7A9A0", "#D9C7B8", "#B98B73"],
    },
    "ocean_calm": {
        "bg": "#EAF1F1",
        "ink": "#1F3A3D",
        "accent": ["#5E8B8B", "#A9C5C1", "#2E5E5A"],
    },
    "charcoal_mono": {
        "bg": "#FAFAF8",
        "ink": "#222222",
        "accent": ["#666666", "#999999", "#111111"],
    },
    "clay_rust": {
        "bg": "#EDE0D3",
        "ink": "#5A2E20",
        "accent": ["#B5502D", "#D9A05B", "#7A6A53"],
    },
}


def get_palette(name: str) -> dict:
    try:
        return PALETTES[name]
    except KeyError as exc:
        raise KeyError(
            f"Unknown palette '{name}'. Available: {', '.join(sorted(PALETTES))}"
        ) from exc
