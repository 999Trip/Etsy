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
) -> Image.Image:
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

    draw = ImageDraw.Draw(template)
    caption_top = y1 + int(h * 0.02)

    if subtitle:
        font = ImageFont.truetype(resolve_font("sans_bold"), int(w * 0.045))
        draw.text((w / 2, caption_top), subtitle, font=font, fill=CAPTION_INK, anchor="ma")
        caption_top += int(w * 0.07)

    if price:
        font = ImageFont.truetype(resolve_font("serif_bold"), int(w * 0.06))
        draw.text((w / 2, caption_top), price, font=font, fill=CAPTION_ACCENT, anchor="ma")
        caption_top += int(w * 0.09)

    # Crop off the template's own leftover caption text below our content
    # (the generated template had its own lower text block that clutters
    # against our custom price/subtitle caption).
    return template.crop((0, 0, w, min(h, caption_top + int(h * 0.02))))


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
