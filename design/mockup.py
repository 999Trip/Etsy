"""Flat-illustration product mockups - preview what a design will look
like on a t-shirt, hoodie, sweatshirt, or mug before spending time in
Printify's own (slower, account-required) mockup generator.

Not photorealistic - drawn the same way as everything else in this repo
(Pillow shapes, flat colors), but the graphic itself is composited in at
its real pixels, so placement, scale, and color contrast against the
garment are accurate previews of the actual print. Garment shapes are
drawn at 2x and downsampled for clean anti-aliased edges.
"""
from __future__ import annotations

from PIL import Image, ImageDraw

CANVAS_SIZE = (1000, 1200)
_SS = 2  # supersampling factor for smooth garment edges

BACKDROP = "#FAFAF8"

GARMENT_COLORS = {
    "white": "#F7F5F0",
    "black": "#1E1E1E",
    "heather_gray": "#ADACA6",
    "navy": "#232B3A",
    "sand": "#D9C9AE",
}


def _shade(hex_color: str, amount: float) -> str:
    """Darken a hex color by `amount` (0-1) for a simple depth cue."""
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    r, g, b = (max(0, int(c * (1 - amount))) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def _fold_shading(canvas: Image.Image, body_mask: Image.Image) -> None:
    """Very light vertical shading so the garment doesn't read as a flat
    color swatch - a soft center highlight and darker sides."""
    w, h = canvas.size
    shade = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    sd.ellipse([w * 0.15, -h * 0.1, w * 0.85, h * 1.1], fill=(255, 255, 255, 18))
    sd.rectangle([0, 0, w * 0.12, h], fill=(0, 0, 0, 28))
    sd.rectangle([w * 0.88, 0, w, h], fill=(0, 0, 0, 28))
    shade.putalpha(Image.composite(shade.split()[3], Image.new("L", (w, h), 0), body_mask))
    canvas.alpha_composite(shade)


def _paste_design(base: Image.Image, design: Image.Image, box: tuple[int, int, int, int]) -> None:
    """Fit `design` inside `box` (x0,y0,x1,y1), preserving aspect ratio, centered."""
    x0, y0, x1, y1 = box
    box_w, box_h = x1 - x0, y1 - y0
    d = design.convert("RGBA")
    scale = min(box_w / d.width, box_h / d.height)
    new_size = (max(1, int(d.width * scale)), max(1, int(d.height * scale)))
    d = d.resize(new_size, Image.LANCZOS)
    px = x0 + (box_w - new_size[0]) // 2
    py = y0 + (box_h - new_size[1]) // 2
    base.alpha_composite(d, (px, py))


def _paste_design_cover(base: Image.Image, design: Image.Image, box: tuple[int, int, int, int]) -> None:
    """Crop+fill `box` with `design` (for an all-over wrap pattern, where
    the whole visible surface should be covered edge to edge, unlike a
    centered box-print graphic - see `_paste_design`)."""
    x0, y0, x1, y1 = box
    box_w, box_h = x1 - x0, y1 - y0
    d = design.convert("RGBA")
    src_ratio, box_ratio = d.width / d.height, box_w / box_h
    if src_ratio > box_ratio:
        new_w = int(d.height * box_ratio)
        x_off = (d.width - new_w) // 2
        d = d.crop((x_off, 0, x_off + new_w, d.height))
    else:
        new_h = int(d.width / box_ratio)
        y_off = (d.height - new_h) // 2
        d = d.crop((0, y_off, d.width, y_off + new_h))
    d = d.resize((int(box_w), int(box_h)), Image.LANCZOS)
    base.alpha_composite(d, (int(x0), int(y0)))


def _draw_garment_body(draw: ImageDraw.ImageDraw, w: int, h: int, color, bg_color, sleeve_frac: float = 0.16) -> None:
    """Torso as a rounded rectangle, short sleeves as small rounded-rect
    tabs overlapping its top corners, and a small neckline notch punched
    out in `bg_color`. Small overlapping rounded rects (rather than large
    ellipses, which read as detached blobs unless very precisely placed)
    keep the sleeves clearly attached to the body at any size."""
    torso_left, torso_top, torso_right, torso_bottom = w * 0.32, h * 0.20, w * 0.68, h * 0.85
    draw.rounded_rectangle([torso_left, torso_top, torso_right, torso_bottom], radius=int(w * 0.05), fill=color)

    sleeve_w = w * 0.12
    sleeve_h = h * sleeve_frac
    sleeve_top = torso_top - h * 0.015
    overlap = sleeve_w * 0.4
    draw.rounded_rectangle(
        [torso_left - sleeve_w + overlap, sleeve_top, torso_left + overlap, sleeve_top + sleeve_h],
        radius=int(sleeve_w * 0.35),
        fill=color,
    )
    draw.rounded_rectangle(
        [torso_right - overlap, sleeve_top, torso_right + sleeve_w - overlap, sleeve_top + sleeve_h],
        radius=int(sleeve_w * 0.35),
        fill=color,
    )

    neck_w, neck_h = w * 0.05, h * 0.028
    neck_cy = h * 0.205
    draw.ellipse([w / 2 - neck_w, neck_cy - neck_h, w / 2 + neck_w, neck_cy + neck_h], fill=bg_color)


def _new_ss_canvas(bg) -> tuple[Image.Image, ImageDraw.ImageDraw, int, int]:
    w, h = CANVAS_SIZE[0] * _SS, CANVAS_SIZE[1] * _SS
    canvas = Image.new("RGBA", (w, h), bg)
    return canvas, ImageDraw.Draw(canvas), w, h


def _finish(canvas: Image.Image) -> Image.Image:
    return canvas.resize(CANVAS_SIZE, Image.LANCZOS)


def mockup_tshirt(design: Image.Image, garment: str = "white", design_scale: float = 0.4) -> Image.Image:
    canvas, draw, w, h = _new_ss_canvas(BACKDROP)
    color = GARMENT_COLORS[garment]
    _draw_garment_body(draw, w, h, color, BACKDROP, sleeve_frac=0.12)

    mask = Image.new("L", (w, h), 0)
    _draw_garment_body(ImageDraw.Draw(mask), w, h, 255, 0, sleeve_frac=0.12)
    _fold_shading(canvas, mask)

    canvas = _finish(canvas)
    cw, ch = CANVAS_SIZE
    box_w, box_h = cw * design_scale, ch * design_scale
    cx, top = cw / 2, ch * 0.34
    _paste_design(canvas, design, (int(cx - box_w / 2), int(top), int(cx + box_w / 2), int(top + box_h)))
    return canvas.convert("RGB")


def mockup_sweatshirt(design: Image.Image, garment: str = "sand", design_scale: float = 0.38) -> Image.Image:
    canvas, draw, w, h = _new_ss_canvas(BACKDROP)
    color = GARMENT_COLORS[garment]
    _draw_garment_body(draw, w, h, color, BACKDROP, sleeve_frac=0.24)

    mask = Image.new("L", (w, h), 0)
    _draw_garment_body(ImageDraw.Draw(mask), w, h, 255, 0, sleeve_frac=0.24)

    ribbing = _shade(color, 0.15)
    torso_box = [w * 0.32, h * 0.20, w * 0.68, h * 0.85]
    draw.line([(torso_box[0] + w * 0.01, torso_box[3] - h * 0.01), (torso_box[2] - w * 0.01, torso_box[3] - h * 0.01)], fill=ribbing, width=int(h * 0.012))

    _fold_shading(canvas, mask)
    canvas = _finish(canvas)

    cw, ch = CANVAS_SIZE
    box_w, box_h = cw * design_scale, ch * design_scale
    cx, top = cw / 2, ch * 0.36
    _paste_design(canvas, design, (int(cx - box_w / 2), int(top), int(cx + box_w / 2), int(top + box_h)))
    return canvas.convert("RGB")


def mockup_hoodie(design: Image.Image, garment: str = "heather_gray", design_scale: float = 0.34) -> Image.Image:
    canvas, draw, w, h = _new_ss_canvas(BACKDROP)
    color = GARMENT_COLORS[garment]
    hood_color = _shade(color, 0.1)

    hood_box = [w * 0.36, h * 0.115, w * 0.64, h * 0.225]
    draw.rounded_rectangle(hood_box, radius=int(w * 0.09), fill=hood_color)

    _draw_garment_body(draw, w, h, color, BACKDROP, sleeve_frac=0.22)

    mask = Image.new("L", (w, h), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle(hood_box, radius=int(w * 0.09), fill=255)
    _draw_garment_body(mdraw, w, h, 255, 0, sleeve_frac=0.22)

    cx = w / 2
    for sign in (-1, 1):
        x = cx + sign * w * 0.028
        draw.line([(x, h * 0.2), (x + sign * w * 0.006, h * 0.29)], fill="#FFFFFF", width=int(w * 0.006))

    pocket_shade = _shade(color, 0.22)
    pocket_y = h * 0.58
    draw.line([(cx - w * 0.15, pocket_y), (cx + w * 0.15, pocket_y)], fill=pocket_shade, width=int(w * 0.004))
    draw.line([(cx - w * 0.15, pocket_y), (cx - w * 0.18, pocket_y + h * 0.09)], fill=pocket_shade, width=int(w * 0.004))
    draw.line([(cx + w * 0.15, pocket_y), (cx + w * 0.18, pocket_y + h * 0.09)], fill=pocket_shade, width=int(w * 0.004))

    _fold_shading(canvas, mask)
    canvas = _finish(canvas)

    cw, ch = CANVAS_SIZE
    box_w, box_h = cw * design_scale, ch * design_scale
    cx, top = cw / 2, ch * 0.38
    _paste_design(canvas, design, (int(cx - box_w / 2), int(top), int(cx + box_w / 2), int(top + box_h)))
    return canvas.convert("RGB")


def mockup_mug(design: Image.Image, garment: str = "white", cover: bool = False) -> Image.Image:
    """`cover=False` (default) centers `design` as a smallish box-print
    patch, as apparel_graphic/canva box-print designs expect. `cover=True`
    wraps it edge to edge across the whole visible mug face instead, for
    an all-over pattern design (see design/generators/pattern.py's
    scatter motifs) - matching how that kind of design actually prints."""
    canvas, draw, w, h = _new_ss_canvas("#E8E6E0")
    color = GARMENT_COLORS[garment]
    outline = _shade(color, 0.2) if garment != "black" else "#3A3A3A"

    body_box = [w * 0.28, h * 0.32, w * 0.68, h * 0.74]
    if cover:
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle(body_box, radius=int(w * 0.018), fill=255)
        design_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        _paste_design_cover(design_layer, design, body_box)
        canvas.paste(design_layer, (0, 0), mask)
        draw.rounded_rectangle(body_box, radius=int(w * 0.018), outline=outline, width=int(w * 0.004))
    else:
        draw.rounded_rectangle(body_box, radius=int(w * 0.018), fill=color, outline=outline, width=int(w * 0.004))

    handle_r = w * 0.075
    handle_cy = (body_box[1] + body_box[3]) / 2
    hx0 = body_box[2] - handle_r * 0.5
    hx1 = body_box[2] + handle_r * 1.5
    hy0 = handle_cy - handle_r * 1.4
    hy1 = handle_cy + handle_r * 1.4
    draw.arc([hx0, hy0, hx1, hy1], start=285, end=75, fill=outline, width=int(w * 0.03))

    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(body_box, radius=int(w * 0.018), fill=255)
    shade = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    box_w = body_box[2] - body_box[0]
    sd.rectangle([body_box[0], body_box[1], body_box[0] + box_w * 0.18, body_box[3]], fill=(255, 255, 255, 55))
    sd.rectangle([body_box[2] - box_w * 0.18, body_box[1], body_box[2], body_box[3]], fill=(0, 0, 0, 40))
    shade.putalpha(Image.composite(shade.split()[3], Image.new("L", (w, h), 0), mask))
    canvas.alpha_composite(shade)

    canvas = _finish(canvas)
    if not cover:
        scale = 1 / _SS
        fbody_box = [c * scale for c in body_box]
        fbox_w = (fbody_box[2] - fbody_box[0]) * 0.7
        fbox_h = (fbody_box[3] - fbody_box[1]) * 0.6
        fcx = (fbody_box[0] + fbody_box[2]) / 2
        fcy = (fbody_box[1] + fbody_box[3]) / 2
        _paste_design(canvas, design, (int(fcx - fbox_w / 2), int(fcy - fbox_h / 2), int(fcx + fbox_w / 2), int(fcy + fbox_h / 2)))
    return canvas.convert("RGB")


FRAME_COLORS = {"black": "#1E1E1E", "white": "#F5F3EE", "wood": "#8A6A4B"}


def mockup_framed_wall(design: Image.Image, frame: str = "black", wall_color: str = "#EDEAE3") -> Image.Image:
    """A portrait design in a simple matted frame hung on a wall - the
    standard second listing photo for printable wall art (quote_poster,
    line_art), giving buyers a sense of scale and how it looks displayed.
    `design` is fit-within (not cropped), matching how a buyer would
    actually print and frame the file."""
    canvas, draw, w, h = _new_ss_canvas(wall_color)
    floor_y = h * 0.88
    draw.rectangle([0, floor_y, w, h], fill=_shade(wall_color, 0.06))

    fcolor = FRAME_COLORS.get(frame, frame)
    frame_box = [w * 0.28, h * 0.08, w * 0.72, h * 0.72]

    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle(
        [frame_box[0] + w * 0.01, frame_box[1] + h * 0.012, frame_box[2] + w * 0.01, frame_box[3] + h * 0.012],
        fill=(0, 0, 0, 60),
    )
    canvas.alpha_composite(shadow)

    draw.rectangle(frame_box, fill=fcolor)
    mat_inset = w * 0.018
    mat_box = [frame_box[0] + mat_inset, frame_box[1] + mat_inset, frame_box[2] - mat_inset, frame_box[3] - mat_inset]
    draw.rectangle(mat_box, fill="#FBFAF7")

    inner_pad = w * 0.012
    art_box = (mat_box[0] + inner_pad, mat_box[1] + inner_pad, mat_box[2] - inner_pad, mat_box[3] - inner_pad)

    pot_cx, pot_bottom = w * 0.85, h * 0.97
    pot_top = pot_bottom - h * 0.09
    draw.polygon(
        [(pot_cx - w * 0.045, pot_bottom), (pot_cx + w * 0.045, pot_bottom), (pot_cx + w * 0.032, pot_top), (pot_cx - w * 0.032, pot_top)],
        fill=_shade(wall_color, 0.35),
    )
    stem_top = pot_top - h * 0.16
    draw.line([(pot_cx, pot_top), (pot_cx, stem_top)], fill="#6B7A5A", width=int(w * 0.006))
    leaf_cy = stem_top - h * 0.02
    for dx, dy, r in [(-0.025, -0.01, 0.045), (0.02, -0.03, 0.04), (0.0, 0.01, 0.038), (0.035, 0.015, 0.035)]:
        draw.ellipse(
            [pot_cx + w * dx - w * r, leaf_cy + h * dy - h * r, pot_cx + w * dx + w * r, leaf_cy + h * dy + h * r],
            fill="#8FA37A",
        )

    canvas = _finish(canvas)
    scale = 1 / _SS
    fart_box = tuple(int(c * scale) for c in art_box)
    _paste_design(canvas, design, fart_box)
    return canvas.convert("RGB")


def mockup_tumbler(design: Image.Image, garment: str = "white") -> Image.Image:
    """A tall handled tumbler with the design wrapped edge to edge across
    the visible body - for the all-over scatter-pattern designs in
    design/generators/pattern.py."""
    canvas, draw, w, h = _new_ss_canvas("#E8E6E0")
    color = GARMENT_COLORS[garment]
    outline = _shade(color, 0.25) if garment != "black" else "#3A3A3A"

    body_box = [w * 0.36, h * 0.2, w * 0.64, h * 0.82]
    radius = int(w * 0.05)

    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(body_box, radius=radius, fill=255)
    design_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    _paste_design_cover(design_layer, design, body_box)
    canvas.paste(design_layer, (0, 0), mask)
    draw.rounded_rectangle(body_box, radius=radius, outline=outline, width=int(w * 0.004))

    lid_box = [body_box[0] - w * 0.01, body_box[1] - h * 0.035, body_box[2] + w * 0.01, body_box[1] + h * 0.02]
    draw.rounded_rectangle(lid_box, radius=int(w * 0.02), fill=color, outline=outline, width=int(w * 0.004))
    straw_x = (lid_box[0] + lid_box[2]) / 2 + w * 0.06
    draw.line([(straw_x, lid_box[1] - h * 0.09), (straw_x, lid_box[1] + h * 0.01)], fill=outline, width=int(w * 0.012))

    handle_w, handle_h = w * 0.09, h * 0.22
    hx0 = body_box[2] - w * 0.01
    hy0 = body_box[1] + h * 0.18
    draw.rounded_rectangle([hx0, hy0, hx0 + handle_w, hy0 + handle_h], radius=int(w * 0.03), outline=outline, width=int(w * 0.018))

    mask2 = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask2).rounded_rectangle(body_box, radius=radius, fill=255)
    shade = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    box_w = body_box[2] - body_box[0]
    sd.rectangle([body_box[0], body_box[1], body_box[0] + box_w * 0.22, body_box[3]], fill=(255, 255, 255, 45))
    sd.rectangle([body_box[2] - box_w * 0.22, body_box[1], body_box[2], body_box[3]], fill=(0, 0, 0, 55))
    shade.putalpha(Image.composite(shade.split()[3], Image.new("L", (w, h), 0), mask2))
    canvas.alpha_composite(shade)

    return _finish(canvas).convert("RGB")
