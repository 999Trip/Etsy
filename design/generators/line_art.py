"""Abstract "boho line art" generator - arches, suns, waves.

This niche (single-line minimalist arches/sun/moon motifs) is one of the
best-selling Etsy digital wall-art categories and, being pure geometry,
is easy to generate proceduraly without any AI image model.
"""
from __future__ import annotations

import math
import random

from design.engine import Canvas, size_px
from design.motifs import ICON_DRAW_FN
from design.palettes import get_palette

MOTIFS = ("arch", "sun", "wave", "moon_phases", *ICON_DRAW_FN.keys())


def _draw_arch(canvas: Canvas, palette: dict, rng: random.Random) -> None:
    cx, cy = canvas.w // 2, int(canvas.h * 0.62)
    max_r = int(min(canvas.w, canvas.h) * 0.34)
    rings = rng.randint(2, 3)
    colors = [palette["ink"], *palette["accent"]]
    rng.shuffle(colors)
    for i in range(rings):
        r = max_r - i * int(max_r * 0.18)
        width = max(4, int(min(canvas.size) * 0.012)) if i == 0 else max(2, int(min(canvas.size) * 0.006))
        bbox = [cx - r, cy - r, cx + r, cy + r]
        canvas.draw.arc(bbox, start=180, end=360, fill=colors[i % len(colors)], width=width)
    # ground line
    gy = cy
    canvas.draw.line([(int(canvas.w * 0.18), gy), (int(canvas.w * 0.82), gy)], fill=palette["ink"], width=max(2, int(min(canvas.size) * 0.004)))
    # small sun disc above the arch
    sun_r = int(max_r * 0.16)
    canvas.draw.ellipse(
        [cx - sun_r, cy - max_r - sun_r * 2, cx + sun_r, cy - max_r],
        fill=palette["accent"][0],
    )


def _draw_sun(canvas: Canvas, palette: dict, rng: random.Random) -> None:
    cx, cy = canvas.w // 2, canvas.h // 2
    r = int(min(canvas.size) * 0.16)
    canvas.draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=palette["ink"], width=max(3, int(min(canvas.size) * 0.008)))
    n_rays = rng.choice([12, 16, 20])
    ray_len = int(r * 0.55)
    for i in range(n_rays):
        angle = (2 * math.pi / n_rays) * i
        x1 = cx + math.cos(angle) * (r + int(r * 0.15))
        y1 = cy + math.sin(angle) * (r + int(r * 0.15))
        x2 = cx + math.cos(angle) * (r + int(r * 0.15) + ray_len)
        y2 = cy + math.sin(angle) * (r + int(r * 0.15) + ray_len)
        color = palette["accent"][i % len(palette["accent"])]
        canvas.draw.line([(x1, y1), (x2, y2)], fill=color, width=max(2, int(min(canvas.size) * 0.006)))


def _draw_wave(canvas: Canvas, palette: dict, rng: random.Random) -> None:
    n_lines = rng.randint(4, 6)
    colors = [palette["ink"], *palette["accent"]]
    amplitude = canvas.h * 0.04
    for i in range(n_lines):
        y0 = canvas.h * (0.3 + i * 0.1)
        points = []
        for x in range(0, canvas.w, 6):
            phase = i * 0.6
            y = y0 + amplitude * math.sin((x / canvas.w) * 4 * math.pi + phase)
            points.append((x, y))
        canvas.draw.line(points, fill=colors[i % len(colors)], width=max(2, int(min(canvas.size) * 0.005)), joint="curve")


def _draw_moon_phases(canvas: Canvas, palette: dict, rng: random.Random) -> None:
    n = 8
    r = int(min(canvas.size) * 0.05)
    spacing = canvas.w // (n + 1)
    cy = canvas.h // 2
    for i in range(n):
        cx = spacing * (i + 1)
        frac = i / (n - 1)  # 0 = new moon, 1 = full moon
        canvas.draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=palette["ink"], width=max(2, int(min(canvas.size) * 0.004)))
        if frac > 0:
            # fill a crescent by drawing a shifted circle in the bg color
            shift = int(r * 2 * (1 - frac))
            canvas.draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=palette["accent"][0])
            canvas.draw.ellipse(
                [cx - r + shift, cy - r, cx + r + shift, cy + r],
                fill=palette["bg"],
            )
            canvas.draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=palette["ink"], width=max(2, int(min(canvas.size) * 0.004)))


def _draw_icon_motif(icon_name):
    def _draw(canvas: Canvas, palette: dict, rng: random.Random) -> None:
        cx, cy = canvas.w // 2, canvas.h // 2
        r = min(canvas.size) * 0.28
        ICON_DRAW_FN[icon_name](canvas.draw, cx, cy, r, palette["ink"], palette["accent"][0])

    return _draw


_MOTIF_FN = {
    "arch": _draw_arch,
    "sun": _draw_sun,
    "wave": _draw_wave,
    "moon_phases": _draw_moon_phases,
    **{name: _draw_icon_motif(name) for name in ICON_DRAW_FN},
}


def generate(
    *,
    motif: str = "arch",
    palette_name: str = "terracotta_boho",
    size_name: str = "poster_18x24",
    seed: int | None = None,
) -> Canvas:
    if motif not in _MOTIF_FN:
        raise ValueError(f"Unknown motif '{motif}'. Available: {', '.join(_MOTIF_FN)}")

    palette = get_palette(palette_name)
    size = size_px(size_name)
    canvas = Canvas(size, palette["bg"])
    rng = random.Random(seed)

    _MOTIF_FN[motif](canvas, palette, rng)

    frame_pad = int(min(size) * 0.06)
    canvas.draw.rectangle(
        [frame_pad, frame_pad, canvas.w - frame_pad, canvas.h - frame_pad],
        outline=palette["accent"][-1],
        width=max(2, int(min(size) * 0.0025)),
    )

    canvas.add_grain(opacity=6, seed=seed)
    return canvas
