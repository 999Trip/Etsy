"""Repeating/tileable pattern generator for digital paper packs.

Digital paper packs (sets of coordinated seamless patterns, sold as a
bundle for scrapbooking / planner covers / junk journaling) are one of
the highest-volume, lowest-effort Etsy digital product categories - and
a great fit for pure procedural generation.
"""
from __future__ import annotations

import math
import random

from design.engine import Canvas, size_px
from design.motifs import draw_icon
from design.palettes import get_palette

# Icon sets for the all-over scattered-icon motifs (tumbler/mug wraps) -
# each name below becomes its own motif via _make_scatter. No "scatter_"
# prefix so humanize(motif) reads cleanly in auto-generated SEO titles
# (e.g. "Night Sky", not "Scatter Night Sky").
SCATTER_ICON_SETS = {
    "night_sky": ("bat", "moon_stars", "star_sparkle"),
    "cozy_critters": ("black_cat", "pumpkin", "ghost"),
    "witchy_purple": ("black_cat", "pumpkin", "moon_stars", "star_sparkle"),
    "jack_o_lanterns": ("jack_o_lantern_face",),
}

MOTIFS = ("dots", "stripes", "checker", "scallop", "arches", *SCATTER_ICON_SETS.keys())


def _dots(canvas: Canvas, palette: dict, rng: random.Random) -> None:
    spacing = int(min(canvas.size) * 0.045)
    r = int(spacing * 0.28)
    colors = palette["accent"]
    for y in range(0, canvas.h + spacing, spacing):
        offset = spacing // 2 if (y // spacing) % 2 else 0
        for x in range(-offset, canvas.w + spacing, spacing):
            color = colors[(x // spacing + y // spacing) % len(colors)]
            canvas.draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def _stripes(canvas: Canvas, palette: dict, rng: random.Random) -> None:
    stripe_w = int(canvas.w * 0.055)
    colors = [palette["bg"], *palette["accent"]]
    x = 0
    i = 0
    while x < canvas.w:
        color = colors[i % len(colors)]
        if color != palette["bg"]:
            canvas.draw.rectangle([x, 0, x + stripe_w, canvas.h], fill=color)
        x += stripe_w
        i += 1


def _checker(canvas: Canvas, palette: dict, rng: random.Random) -> None:
    cell = int(min(canvas.size) * 0.06)
    colors = [palette["bg"], palette["accent"][0]]
    for row, y in enumerate(range(0, canvas.h, cell)):
        for col, x in enumerate(range(0, canvas.w, cell)):
            if (row + col) % 2:
                canvas.draw.rectangle([x, y, x + cell, y + cell], fill=colors[1])


def _scallop(canvas: Canvas, palette: dict, rng: random.Random) -> None:
    r = int(min(canvas.size) * 0.045)
    colors = palette["accent"]
    row = 0
    y = -r
    while y < canvas.h + r:
        offset = r if row % 2 else 0
        col = 0
        x = -r + offset
        while x < canvas.w + r:
            color = colors[(row + col) % len(colors)]
            canvas.draw.arc([x - r, y - r, x + r, y + r], start=0, end=180, fill=color, width=max(3, int(r * 0.18)))
            x += 2 * r
            col += 1
        y += r
        row += 1


def _arches(canvas: Canvas, palette: dict, rng: random.Random) -> None:
    r = int(min(canvas.size) * 0.05)
    colors = palette["accent"]
    row = 0
    y = canvas.h
    while y > -r * 2:
        offset = r if row % 2 else 0
        col = 0
        x = offset
        while x < canvas.w + r:
            color = colors[(row + col) % len(colors)]
            canvas.draw.arc([x - r, y - 2 * r, x + r, y], start=180, end=360, fill=color, width=max(3, int(r * 0.16)))
            x += 2 * r
            col += 1
        y -= int(r * 1.4)
        row += 1


def _make_scatter(icons: tuple[str, ...]):
    """All-over scattered-icon pattern - random position/size/rotation
    (rotation approximated by simply varying size, since the icon
    functions don't support arbitrary rotation) of a small icon set
    across the canvas, for tumbler/mug wraps and digital paper. This is
    original artwork built from our own icon library, not a copy of any
    specific commercial product design."""

    def _draw(canvas: Canvas, palette: dict, rng: random.Random) -> None:
        colors = [palette["ink"], *palette["accent"]]
        density = 46 if len(icons) > 1 else 70
        count = int((canvas.w * canvas.h) / (min(canvas.size) ** 2) * density)
        min_dim = min(canvas.size)
        for _ in range(count):
            icon = rng.choice(icons)
            cx = rng.uniform(0, canvas.w)
            cy = rng.uniform(0, canvas.h)
            r = min_dim * rng.uniform(0.025, 0.06)
            ink = rng.choice(colors)
            accent = rng.choice([c for c in colors if c != ink] or colors)
            draw_icon(canvas.draw, icon, cx, cy, r, ink, accent)

    return _draw


_MOTIF_FN = {
    "dots": _dots,
    "stripes": _stripes,
    "checker": _checker,
    "scallop": _scallop,
    "arches": _arches,
    **{name: _make_scatter(icons) for name, icons in SCATTER_ICON_SETS.items()},
}


def generate(
    *,
    motif: str = "dots",
    palette_name: str = "blush_neutral",
    size_name: str = "square_12x12",
    seed: int | None = None,
) -> Canvas:
    if motif not in _MOTIF_FN:
        raise ValueError(f"Unknown motif '{motif}'. Available: {', '.join(_MOTIF_FN)}")

    palette = get_palette(palette_name)
    size = size_px(size_name)
    canvas = Canvas(size, palette["bg"])
    rng = random.Random(seed)

    _MOTIF_FN[motif](canvas, palette, rng)
    canvas.add_grain(opacity=4, seed=seed)
    return canvas
