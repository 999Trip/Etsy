"""Generate accurate Pinterest pins by compositing a real product photo
into a Canva-made decorative template - not by asking Canva's AI to
render the product itself.

Canva's generate-design ignored an uploaded product-photo asset and
invented its own (different, inaccurate) tumbler/cat artwork when asked
to "use" that photo in a pin (see git history / session notes around
the first pin attempt) - the same class of problem as the calendar date
grid: reliable for decorative art, unreliable for anything that has to
exactly match specific real content. The fix is the same pattern as
pipeline/canva_import.py's illustrated-calendar-background workflow:
use Canva only for a purely decorative frame with a blank safe-zone,
and composite the real photo in locally.

Usage:
    python -m pipeline.pinterest_pins \\
        --template /tmp/pin_template1.png \\
        --photo <path or URL to the real product photo> \\
        --title "Halloween Tumbler" --subtitle "Cat in Pumpkin Design" \\
        --price "$47.99" --out output/pins/cat_in_pumpkin_pin.png
"""
from __future__ import annotations

import argparse
from pathlib import Path

import requests
from PIL import Image, ImageDraw

from design.fonts import resolve_font
from PIL import ImageFont

# Safe-zone box detected in the generated template (pin_template1.png,
# 1000x1500) - inset from the raw detected blank-box bounds to clear the
# small corner icon accents.
TEMPLATE_SAFE_ZONE = (159, 624, 840, 1070)
CAPTION_INK = "#2A1810"
CAPTION_ACCENT = "#B5502D"

# The bold studio-backdrop template (pin_bold1.png) - a purple/orange
# gradient scene with a white product card as the safe-zone and its own
# "HALLOWEEN FAVES" header baked in, so callers using it should pass
# subtitle/price only (no separate title needed).
BOLD_TEMPLATE_SAFE_ZONE = (310, 550, 693, 1130)
# Crop the template here *before* adding our own caption - its own
# trailing "Shop the best this season!" text lives below this and would
# otherwise clash with the per-product subtitle/price we add.
BOLD_TEMPLATE_CONTENT_BOTTOM = 1183


def _load_photo(photo: str) -> Image.Image:
    if photo.startswith("http"):
        resp = requests.get(photo, timeout=60)
        resp.raise_for_status()
        from io import BytesIO

        return Image.open(BytesIO(resp.content)).convert("RGB")
    return Image.open(photo).convert("RGB")


def make_pin(
    template_path: str,
    photo: str,
    title: str,
    subtitle: str = "",
    price: str = "",
    safe_zone: tuple[int, int, int, int] = TEMPLATE_SAFE_ZONE,
    content_bottom: int | None = None,
    caption_ink: str = CAPTION_INK,
    caption_accent: str = CAPTION_ACCENT,
) -> Image.Image:
    template = Image.open(template_path).convert("RGB")
    w, h = template.size
    if content_bottom is not None:
        template = template.crop((0, 0, w, content_bottom))
        h = content_bottom
    product = _load_photo(photo)

    x0, y0, x1, y1 = safe_zone
    box_w, box_h = x1 - x0, y1 - y0
    scale = min(box_w / product.width, box_h / product.height)
    new_size = (max(1, round(product.width * scale)), max(1, round(product.height * scale)))
    product = product.resize(new_size, Image.LANCZOS)
    px = x0 + (box_w - new_size[0]) // 2
    py = y0 + (box_h - new_size[1]) // 2
    template.paste(product, (px, py))

    draw = ImageDraw.Draw(template)
    caption_top = y1 + int(h * 0.02)

    if subtitle:
        font = ImageFont.truetype(resolve_font("sans_bold"), int(w * 0.045))
        draw.text((w / 2, caption_top), subtitle, font=font, fill=caption_ink, anchor="ma")
        caption_top += int(w * 0.07)

    if price:
        font = ImageFont.truetype(resolve_font("serif_bold"), int(w * 0.06))
        draw.text((w / 2, caption_top), price, font=font, fill=caption_accent, anchor="ma")
        caption_top += int(w * 0.09)

    # Crop off the template's own leftover caption text below our content
    # (only relevant when content_bottom wasn't already used to remove
    # it up front - kept for templates that don't need pre-cropping).
    return template.crop((0, 0, w, min(h, caption_top + int(h * 0.02))))


def make_bold_pin(
    photo: str,
    subtitle: str,
    price: str,
    template_path: str = "/tmp/canva_candidates/pin_bold1.png",
    safe_zone: tuple[int, int, int, int] = BOLD_TEMPLATE_SAFE_ZONE,
    banner_color: str = "#2E1A47",
) -> Image.Image:
    """For the studio-backdrop bold template specifically: its own
    trailing "Shop the best this season!" text sits close enough below
    the product card that a per-product caption can't just be added
    below it without either overlapping or being cropped away (tried
    both - see git history). Painting a solid banner over that region
    instead guarantees it's fully hidden and our caption reads cleanly
    on a high-contrast background regardless of the gradient underneath."""
    template = Image.open(template_path).convert("RGB")
    w, h = template.size
    product = _load_photo(photo)

    x0, y0, x1, y1 = safe_zone
    box_w, box_h = x1 - x0, y1 - y0
    scale = min(box_w / product.width, box_h / product.height)
    new_size = (max(1, round(product.width * scale)), max(1, round(product.height * scale)))
    product = product.resize(new_size, Image.LANCZOS)
    px = x0 + (box_w - new_size[0]) // 2
    py = y0 + (box_h - new_size[1]) // 2
    template.paste(product, (px, py))

    banner_top = y1 + int(h * 0.015)
    banner_bottom = min(h, banner_top + int(h * 0.15))
    draw = ImageDraw.Draw(template)
    draw.rectangle([0, banner_top, w, banner_bottom], fill=banner_color)

    subtitle_font = ImageFont.truetype(resolve_font("sans_bold"), int(w * 0.045))
    price_font = ImageFont.truetype(resolve_font("serif_bold"), int(w * 0.065))
    draw.text((w / 2, banner_top + int(h * 0.035)), subtitle, font=subtitle_font, fill="#FFFFFF", anchor="ma")
    draw.text((w / 2, banner_top + int(h * 0.085)), price, font=price_font, fill="#FFD9A0", anchor="ma")

    return template.crop((0, 0, w, banner_bottom))


def main() -> None:
    parser = argparse.ArgumentParser(description="Composite a real product photo into a Canva pin template.")
    parser.add_argument("--template", required=True, help="Path to the exported Canva pin template PNG")
    parser.add_argument("--photo", required=True, help="Path or URL to the real product photo")
    parser.add_argument("--title", required=True, help="(unused directly - template already has the title baked in; kept for record-keeping)")
    parser.add_argument("--subtitle", default="")
    parser.add_argument("--price", default="")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    pin = make_pin(args.template, args.photo, args.title, args.subtitle, args.price)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pin.save(out_path, "PNG")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
