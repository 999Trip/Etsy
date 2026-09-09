"""Minimalist typography poster generator (the most common Etsy printable)."""
from __future__ import annotations

from design.engine import Canvas, draw_centered_multiline, fit_text_block, size_px
from design.fonts import resolve_font
from design.palettes import get_palette


def generate(
    *,
    quote: str,
    author: str | None = None,
    palette_name: str = "sage_minimal",
    size_name: str = "poster_18x24",
    uppercase: bool = True,
    seed: int | None = None,
) -> Canvas:
    palette = get_palette(palette_name)
    size = size_px(size_name)
    canvas = Canvas(size, palette["bg"])

    margin = int(min(size) * 0.14)
    max_w = canvas.w - 2 * margin
    max_h = int(canvas.h * 0.55)

    display_text = quote.upper() if uppercase else quote
    font_path = resolve_font("serif_bold" if uppercase else "serif")
    font, wrapped, spacing = fit_text_block(
        canvas.draw,
        display_text,
        font_path,
        max_w,
        max_h,
        start_size=int(min(size) * 0.14),
        min_size=24,
    )

    center_y = int(canvas.h * 0.46)
    box = draw_centered_multiline(canvas, wrapped, font, palette["ink"], (canvas.w // 2, center_y), spacing)

    # A thin accent rule under the quote is a very common printable motif.
    rule_y = box[3] + int(min(size) * 0.035)
    rule_w = int(canvas.w * 0.12)
    canvas.draw.line(
        [(canvas.w // 2 - rule_w // 2, rule_y), (canvas.w // 2 + rule_w // 2, rule_y)],
        fill=palette["accent"][0],
        width=max(2, int(min(size) * 0.004)),
    )

    if author:
        from PIL import ImageFont

        author_font_path = resolve_font("sans")
        author_size = max(18, int(min(size) * 0.028))
        af = ImageFont.truetype(author_font_path, author_size)
        draw_centered_multiline(
            canvas,
            f"— {author.upper()}",
            af,
            palette["accent"][0],
            (canvas.w // 2, rule_y + int(min(size) * 0.05)),
            spacing=0,
        )

    # Simple corner frame - a cheap way to make a plain background read as
    # "designed" rather than empty.
    frame_pad = int(min(size) * 0.06)
    frame_w = max(2, int(min(size) * 0.0025))
    canvas.draw.rectangle(
        [frame_pad, frame_pad, canvas.w - frame_pad, canvas.h - frame_pad],
        outline=palette["accent"][-1],
        width=frame_w,
    )

    canvas.add_grain(opacity=6, seed=seed)
    return canvas
