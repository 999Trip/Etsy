"""Print-on-demand graphic generator - t-shirts, sweatshirts, mugs, etc.

Unlike the wall-art generators, this renders onto a *transparent*
background (see ``Canvas.transparent``) so the garment or mug color shows
through everywhere the design doesn't paint, and uses a single ink color
for the icon (a flat silhouette) so the artwork works on any light-colored
product without color-matching. For dark garments you'll typically want a
white/inverted version of the art - Printify's editor can usually do that
recolor for you when you place the design.

Automatically lays out icon + text stacked (portrait/square canvases,
e.g. an apparel print area) or side-by-side (landscape canvases, e.g. a
mug wrap) based on the chosen size's aspect ratio.
"""
from __future__ import annotations

from design.engine import Canvas, draw_centered_multiline, fit_text_block, size_px
from design.fonts import resolve_font
from design.motifs import draw_icon
from design.palettes import get_palette


def generate(
    *,
    motif: str,
    palette_name: str = "clay_rust",
    text: str | None = None,
    size_name: str = "apparel_12x16",
    seed: int | None = None,
) -> Canvas:
    palette = get_palette(palette_name)
    size = size_px(size_name)
    canvas = Canvas.transparent(size)
    ink = palette["ink"]
    accent = palette["accent"][0]

    landscape = canvas.w > canvas.h * 1.3

    if landscape:
        icon_cx, icon_cy = canvas.w * 0.24, canvas.h * 0.5
        icon_r = min(canvas.w * 0.4, canvas.h * 0.42)
        text_box = (canvas.w * 0.42, canvas.h * 0.14, canvas.w * 0.94, canvas.h * 0.86)
    else:
        icon_cx, icon_cy = canvas.w * 0.5, canvas.h * 0.4
        icon_r = min(canvas.w * 0.34, canvas.h * 0.28)
        text_box = (canvas.w * 0.08, canvas.h * 0.62, canvas.w * 0.92, canvas.h * 0.92)

    draw_icon(canvas.draw, motif, icon_cx, icon_cy, icon_r, ink, accent)

    if text:
        box_w = int(text_box[2] - text_box[0])
        box_h = int(text_box[3] - text_box[1])
        center = (int((text_box[0] + text_box[2]) / 2), int((text_box[1] + text_box[3]) / 2))
        font_path = resolve_font("sans_bold")
        font, wrapped, spacing = fit_text_block(
            canvas.draw,
            text.upper(),
            font_path,
            box_w,
            box_h,
            start_size=int(min(size) * 0.14),
            min_size=20,
            line_spacing=0.3,
        )
        draw_centered_multiline(canvas, wrapped, font, ink, center, spacing)

    return canvas
