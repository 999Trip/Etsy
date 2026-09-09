"""Shared drawing/export primitives used by every design generator.

Nothing in this file is niche-specific - it's the equivalent of a tiny
"design system" (canvas sizing, text fitting/wrapping, grain texture,
export to print-ready PNG/PDF and a web preview JPG) that
``design/generators/*.py`` build on top of.
"""
from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

# Etsy printables are conventionally sold at 300 DPI. Physical (POD)
# prints use the same DPI; the actual pixel size just needs to match
# whatever print area the Printify blueprint expects.
DPI = 300

# Common digital-printable / wall-art sizes, in inches.
SIZES_IN: dict[str, tuple[float, float]] = {
    "poster_18x24": (18, 24),
    "poster_24x36": (24, 36),
    "letter_8.5x11": (8.5, 11),
    "a4": (8.27, 11.69),
    "square_12x12": (12, 12),
    "5x7": (5, 7),
    # Print-on-demand graphic areas. These are safe-zone sizes for the
    # artwork file, not the finished garment/mug dimensions.
    "apparel_12x16": (12, 16),  # DTG-friendly design area for tees/sweatshirts/hoodies
    "mug_9x4": (9, 4),  # roughly the wrap-around print area on an 11oz mug
}


def size_px(size_name: str, dpi: int = DPI) -> tuple[int, int]:
    w_in, h_in = SIZES_IN[size_name]
    return int(round(w_in * dpi)), int(round(h_in * dpi))


class Canvas:
    """A PIL image + draw context with a few export helpers."""

    def __init__(self, size: tuple[int, int], background: str):
        self.image = Image.new("RGB", size, background)
        self.draw = ImageDraw.Draw(self.image)
        self.size = size

    @classmethod
    def transparent(cls, size: tuple[int, int]) -> "Canvas":
        """A canvas with a fully transparent background, for print-on-demand
        artwork (t-shirts, mugs, ...) where the garment/product color shows
        through everywhere the design doesn't paint."""
        canvas = cls.__new__(cls)
        canvas.image = Image.new("RGBA", size, (0, 0, 0, 0))
        canvas.draw = ImageDraw.Draw(canvas.image)
        canvas.size = size
        return canvas

    @property
    def w(self) -> int:
        return self.size[0]

    @property
    def h(self) -> int:
        return self.size[1]

    def add_grain(self, opacity: int = 10, seed: int | None = None) -> None:
        """Overlay a very subtle noise texture for a less "flat vector" look.

        No-op on a transparent (RGBA) canvas - grain is a paper-texture
        effect for printable posters, not meaningful for a print-on-demand
        graphic that sits on a garment color.
        """
        if self.image.mode == "RGBA":
            return
        rng = random.Random(seed)
        noise = Image.new("L", self.size)
        noise.putdata([rng.randint(0, 255) for _ in range(self.w * self.h)])
        noise = noise.point(lambda p: 128 + (p - 128) * opacity // 100)
        noise_rgb = Image.merge("RGB", (noise, noise, noise))
        self.image = Image.blend(self.image, noise_rgb, opacity / 400)
        self.draw = ImageDraw.Draw(self.image)

    def add_distress(self, intensity: float = 0.35, seed: int | None = None) -> None:
        """Rough up a transparent canvas's alpha channel with a blotchy
        noise mask - the worn, screen-printed-onto-fabric look behind the
        vintage/retro Halloween & fall apparel trend (as opposed to a
        crisp flat-vector print). No-op on an opaque (RGB) canvas, where
        ``add_grain`` is the equivalent paper-texture effect.
        """
        if self.image.mode != "RGBA":
            return
        rng = random.Random(seed)
        # Low-res noise, blurred and upscaled, reads as mottled blotches
        # rather than per-pixel static.
        small = (max(1, self.w // 40), max(1, self.h // 40))
        noise = Image.new("L", small)
        noise.putdata([rng.randint(0, 255) for _ in range(small[0] * small[1])])
        noise = noise.resize(self.size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(2))

        floor = int(255 * (1 - intensity))
        mask = noise.point(lambda p: floor + int(intensity * p))

        r, g, b, a = self.image.split()
        a = ImageChops.multiply(a, mask)
        self.image = Image.merge("RGBA", (r, g, b, a))
        self.draw = ImageDraw.Draw(self.image)

    def vignette(self, strength: float = 0.15) -> None:
        """Very light edge darkening to add depth to flat backgrounds."""
        if self.image.mode == "RGBA":
            return
        mask = Image.new("L", self.size, 0)
        mdraw = ImageDraw.Draw(mask)
        pad = int(min(self.size) * 0.08)
        mdraw.ellipse([-pad, -pad, self.w + pad, self.h + pad], fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(min(self.size) // 6))
        dark = Image.new("RGB", self.size, (0, 0, 0))
        self.image = Image.composite(self.image, dark, mask.point(lambda p: 255 - int(strength * (255 - p))))
        self.draw = ImageDraw.Draw(self.image)

    def save_png(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.image.save(path, "PNG")

    def save_pdf(self, path: str | Path, dpi: int = DPI) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        image = self.image.convert("RGB") if self.image.mode == "RGBA" else self.image
        image.save(path, "PDF", resolution=dpi)

    def save_preview_jpg(
        self, path: str | Path, max_dim: int = 2000, quality: int = 87, backdrop: str = "#FFFFFF"
    ) -> None:
        """Save a web-sized JPG preview. A transparent (RGBA) canvas is
        flattened onto ``backdrop`` first - mimicking a light garment/mug
        color - so print-on-demand previews don't render as solid black."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        preview = self.image.copy()
        preview.thumbnail((max_dim, max_dim))
        if preview.mode == "RGBA":
            flat = Image.new("RGB", preview.size, backdrop)
            flat.paste(preview, (0, 0), preview)
            preview = flat
        preview.convert("RGB").save(path, "JPEG", quality=quality)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    """Greedy word-wrap that respects explicit newlines in the input."""
    out_lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            out_lines.append("")
            continue
        line = words[0]
        for word in words[1:]:
            trial = f"{line} {word}"
            if draw.textlength(trial, font=font) <= max_width:
                line = trial
            else:
                out_lines.append(line)
                line = word
        out_lines.append(line)
    return "\n".join(out_lines)


def fit_text_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: str,
    max_width: int,
    max_height: int,
    start_size: int = 240,
    min_size: int = 24,
    step: int = 4,
    line_spacing: float = 0.4,
) -> tuple[ImageFont.FreeTypeFont, str, int]:
    """Find the largest font size (and matching word-wrap) that fits the box.

    Returns (font, wrapped_text, spacing_px).
    """
    size = start_size
    while size >= min_size:
        font = ImageFont.truetype(font_path, size)
        wrapped = wrap_text(draw, text, font, max_width)
        spacing = int(size * line_spacing)
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align="center", spacing=spacing)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if w <= max_width and h <= max_height:
            return font, wrapped, spacing
        size -= step
    font = ImageFont.truetype(font_path, min_size)
    spacing = int(min_size * line_spacing)
    return font, wrap_text(draw, text, font, max_width), spacing


def draw_centered_multiline(
    canvas: Canvas,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
    center: tuple[int, int],
    spacing: int,
) -> tuple[int, int, int, int]:
    """Draw text centered on ``center``. Returns the bounding box drawn."""
    bbox = canvas.draw.multiline_textbbox((0, 0), text, font=font, align="center", spacing=spacing)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = center[0] - w / 2 - bbox[0]
    y = center[1] - h / 2 - bbox[1]
    canvas.draw.multiline_text((x, y), text, font=font, fill=fill, align="center", spacing=spacing)
    return (int(x), int(y), int(x + w), int(y + h))
