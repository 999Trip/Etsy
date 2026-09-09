"""Reusable seasonal icon silhouettes (pumpkin, ghost, bat, leaf, ...).

Each ``draw_*`` function renders one icon centered at ``(cx, cy)`` inside
roughly a ``2r x 2r`` box, in a single flat style so it reads cleanly both
as a colored accent on a printable poster (design/generators/line_art.py)
and as a single-ink silhouette on a transparent apparel/mug graphic
(design/generators/apparel_graphic.py).
"""
from __future__ import annotations

import math
from typing import Callable

from PIL import ImageDraw


def _w(r: float, frac: float = 0.05) -> int:
    return max(2, int(r * frac))


def draw_pumpkin(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, ink, accent=None) -> None:
    body_w, body_h = r * 1.7, r * 1.35
    width = _w(r, 0.055)
    lobes = 3
    for i in range(lobes):
        t = (i - (lobes - 1) / 2) / lobes
        x = cx + t * body_w * 0.85
        w = body_w * (0.55 if i == (lobes - 1) / 2 else 0.5)
        draw.arc([x - w / 2, cy - body_h / 2, x + w / 2, cy + body_h / 2], 0, 360, fill=ink, width=width)
    stem_color = accent or ink
    stem_w, stem_h = r * 0.16, r * 0.32
    top = cy - body_h / 2
    draw.polygon(
        [
            (cx - stem_w / 2, top),
            (cx + stem_w / 2, top),
            (cx + stem_w * 0.35, top - stem_h),
            (cx - stem_w * 0.35, top - stem_h),
        ],
        fill=stem_color,
    )


def draw_ghost(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, ink, accent=None) -> None:
    width = _w(r, 0.06)
    body_w, body_h = r * 1.5, r * 1.6
    top = cy - body_h / 2
    bottom = cy + body_h / 2
    left, right = cx - body_w / 2, cx + body_w / 2

    # Rounded head via the top half of an ellipse.
    draw.arc([left, top, right, top + body_h * 0.9], 180, 360, fill=ink, width=width)
    # Straight sides down to where the scalloped hem starts.
    hem_y = top + body_h * 0.62
    draw.line([(left, top + body_h * 0.45), (left, hem_y)], fill=ink, width=width)
    draw.line([(right, top + body_h * 0.45), (right, hem_y)], fill=ink, width=width)

    # Scalloped bottom hem (a row of small bumps).
    bumps = 4
    bump_w = body_w / bumps
    for i in range(bumps):
        bx = left + bump_w * i
        draw.arc([bx, hem_y - bump_w * 0.35, bx + bump_w, bottom], 0, 180, fill=ink, width=width)

    eye_r = r * 0.09
    for dx in (-body_w * 0.18, body_w * 0.18):
        ex, ey = cx + dx, cy - body_h * 0.05
        draw.ellipse([ex - eye_r, ey - eye_r, ex + eye_r, ey + eye_r], fill=ink)


def draw_bat(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, ink, accent=None) -> None:
    body_r = r * 0.28
    wing_span = r * 1.5

    def wing_points(sign: int) -> list[tuple[float, float]]:
        bx = cx + sign * body_r * 0.7
        return [
            (bx, cy - body_r * 0.6),
            (bx + sign * wing_span * 0.35, cy - wing_span * 0.55),
            (bx + sign * wing_span * 0.62, cy - wing_span * 0.22),
            (bx + sign * wing_span, cy + wing_span * 0.12),
            (bx + sign * wing_span * 0.6, cy - wing_span * 0.02),
            (bx + sign * wing_span * 0.32, cy + wing_span * 0.28),
            (bx + sign * wing_span * 0.12, cy + body_r * 0.2),
            (bx, cy + body_r * 0.5),
        ]

    draw.polygon(wing_points(1), fill=ink)
    draw.polygon(wing_points(-1), fill=ink)
    draw.ellipse([cx - body_r, cy - body_r, cx + body_r, cy + body_r], fill=ink)
    ear = body_r * 0.9
    draw.polygon(
        [(cx - body_r * 0.6, cy - body_r * 0.6), (cx - body_r * 0.15, cy - body_r * 0.6), (cx - body_r * 0.35, cy - body_r * 0.6 - ear)],
        fill=ink,
    )
    draw.polygon(
        [(cx + body_r * 0.6, cy - body_r * 0.6), (cx + body_r * 0.15, cy - body_r * 0.6), (cx + body_r * 0.35, cy - body_r * 0.6 - ear)],
        fill=ink,
    )


def draw_leaf(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, ink, accent=None) -> None:
    width = _w(r, 0.05)
    points = []
    steps = 24
    for i in range(steps + 1):
        t = i / steps
        angle = math.pi * t
        x = cx + math.sin(angle) * r * 0.85
        y = cy - r + t * 2 * r
        points.append((x, y))
    for i in range(steps + 1):
        t = i / steps
        angle = math.pi * t
        x = cx - math.sin(angle) * r * 0.55
        y = cy + r - t * 2 * r
        points.append((x, y))
    draw.polygon(points, outline=ink, width=width)
    draw.line([(cx, cy - r * 0.95), (cx, cy + r)], fill=ink, width=max(1, width - 1))
    for frac in (0.25, 0.55):
        vy = cy - r + 2 * r * frac
        draw.line([(cx, vy), (cx + r * 0.4 * (1 - frac), vy - r * 0.15)], fill=ink, width=max(1, width - 1))
        draw.line([(cx, vy), (cx - r * 0.4 * (1 - frac), vy - r * 0.15)], fill=ink, width=max(1, width - 1))
    stem_color = accent or ink
    draw.line([(cx, cy + r), (cx, cy + r * 1.25)], fill=stem_color, width=width)


def _star(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, fill) -> None:
    points = []
    for i in range(8):
        angle = math.pi / 4 * i - math.pi / 2
        radius = r if i % 2 == 0 else r * 0.42
        points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    draw.polygon(points, fill=fill)


def draw_moon_stars(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, ink, accent=None) -> None:
    width = _w(r, 0.09)
    draw.arc([cx - r, cy - r, cx + r, cy + r], 50, 300, fill=ink, width=width)
    star_color = accent or ink
    _star(draw, cx + r * 0.95, cy - r * 0.75, r * 0.16, star_color)
    _star(draw, cx + r * 1.35, cy - r * 0.15, r * 0.1, star_color)
    _star(draw, cx + r * 0.7, cy + r * 0.85, r * 0.11, star_color)


def draw_witch_hat(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, ink, accent=None) -> None:
    width = _w(r, 0.06)
    brim_w, brim_h = r * 1.9, r * 0.36
    brim_bbox = [cx - brim_w / 2, cy + r * 0.55 - brim_h / 2, cx + brim_w / 2, cy + r * 0.55 + brim_h / 2]
    draw.arc(brim_bbox, 0, 180, fill=ink, width=width)
    draw.line([(cx - brim_w / 2, cy + r * 0.55), (cx + brim_w / 2, cy + r * 0.55)], fill=ink, width=width)

    tip_bend = r * 0.18
    cone = [
        (cx, cy - r),
        (cx + r * 0.5, cy + r * 0.55),
        (cx - r * 0.62, cy + r * 0.55),
    ]
    draw.line([cone[0], cone[1]], fill=ink, width=width)
    draw.line([cone[1], cone[2]], fill=ink, width=width)
    draw.line(
        [cone[2], (cx - tip_bend, cy - r * 0.35), cone[0]],
        fill=ink,
        width=width,
        joint="curve",
    )

    band_color = accent or ink
    band_y = cy + r * 0.3
    draw.line([(cx - r * 0.55, band_y), (cx + r * 0.42, band_y)], fill=band_color, width=width)
    buckle_r = r * 0.14
    draw.rectangle(
        [cx - r * 0.12 - buckle_r, band_y - buckle_r, cx - r * 0.12 + buckle_r, band_y + buckle_r],
        outline=band_color,
        width=max(2, width - 1),
    )


def draw_black_cat(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, ink, accent=None) -> None:
    body_bbox = [cx - r * 0.55, cy - r * 0.15, cx + r * 0.55, cy + r]
    draw.ellipse(body_bbox, fill=ink)
    head_r = r * 0.42
    head_cx, head_cy = cx - r * 0.15, cy - r * 0.55
    draw.ellipse([head_cx - head_r, head_cy - head_r, head_cx + head_r, head_cy + head_r], fill=ink)
    ear = head_r * 0.75
    draw.polygon(
        [(head_cx - head_r * 0.7, head_cy - head_r * 0.5), (head_cx - head_r * 0.1, head_cy - head_r * 0.7), (head_cx - head_r * 0.4, head_cy - head_r - ear)],
        fill=ink,
    )
    draw.polygon(
        [(head_cx + head_r * 0.7, head_cy - head_r * 0.5), (head_cx + head_r * 0.1, head_cy - head_r * 0.7), (head_cx + head_r * 0.4, head_cy - head_r - ear)],
        fill=ink,
    )
    # Curled tail, drawn as a thick arc sweeping up from the body.
    tail_r = r * 0.55
    tail_cx, tail_cy = cx + r * 0.55, cy + r * 0.25
    draw.arc(
        [tail_cx - tail_r, tail_cy - tail_r * 1.6, tail_cx + tail_r, tail_cy + tail_r * 0.4],
        200,
        20,
        fill=ink,
        width=_w(r, 0.14),
    )


ICON_DRAW_FN: dict[str, Callable] = {
    "pumpkin": draw_pumpkin,
    "ghost": draw_ghost,
    "bat": draw_bat,
    "leaf": draw_leaf,
    "moon_stars": draw_moon_stars,
    "witch_hat": draw_witch_hat,
    "black_cat": draw_black_cat,
}


def draw_icon(draw: ImageDraw.ImageDraw, name: str, cx: float, cy: float, r: float, ink, accent=None) -> None:
    if name not in ICON_DRAW_FN:
        raise ValueError(f"Unknown icon '{name}'. Available: {', '.join(ICON_DRAW_FN)}")
    ICON_DRAW_FN[name](draw, cx, cy, r, ink, accent)
