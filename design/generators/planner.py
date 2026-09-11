"""Printable planner/tracker generator - weekly planners, budget
trackers, habit trackers, checklists.

Distinct from the wall-art generators: these are functional documents
(tables, grids, checkboxes) rather than illustrations, targeting Etsy's
planner/template category - per 2026 trend research this is one of the
fastest-growing digital product categories (ahead of decorative wall
art), with budget trackers and productivity planners specifically called
out as top sellers.

Deliberately low-ink: the page background is always plain white
regardless of the chosen palette (which only drives text/line color) -
"low-ink" printables (buyers save money by not printing solid colored
backgrounds) are a named 2026 trend in their own right. Exception:
mood_tracker and weekly_todo are illustrated-parchment templates
(modeled on trending hand-drawn cauldron/checklist printables) and
paint their own warm cream page tint instead of using PAGE_BG - that
look is the point for those two, not an oversight.
"""
from __future__ import annotations

import calendar as _calendar
import math

from PIL import ImageColor, ImageFont

from design.engine import Canvas, draw_centered_multiline, fit_text_block, size_px
from design.fonts import resolve_font
from design.motifs import draw_icon
from design.palettes import get_palette

TEMPLATES = (
    "weekly_planner",
    "budget_tracker",
    "habit_tracker",
    "checklist",
    "monthly_calendar",
    "mood_tracker",
    "weekly_todo",
)

PAGE_BG = "#FFFFFF"

DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
CALENDAR_DAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
BUDGET_CATEGORIES = [
    "Housing",
    "Utilities",
    "Groceries",
    "Transportation",
    "Insurance",
    "Debt Payments",
    "Subscriptions",
    "Personal",
    "Savings",
    "Other",
]


def _header(canvas: Canvas, palette: dict, header_text: str, margin: int) -> int:
    max_width = canvas.w - 2 * margin
    max_height = int(canvas.w * 0.11)
    font, wrapped, spacing = fit_text_block(
        canvas.draw,
        header_text.upper(),
        resolve_font("serif_bold"),
        max_width,
        max_height,
        start_size=int(canvas.w * 0.055),
        min_size=int(canvas.w * 0.02),
        line_spacing=0.25,
    )
    top = margin + int(canvas.w * 0.02)
    box = draw_centered_multiline(canvas, wrapped, font, palette["ink"], (canvas.w // 2, top + max_height // 2), spacing)

    rule_y = box[3] + int(canvas.w * 0.02)
    canvas.draw.line(
        [(margin, rule_y), (canvas.w - margin, rule_y)], fill=palette["accent"][0], width=max(2, int(canvas.w * 0.0025))
    )
    return rule_y + int(canvas.w * 0.025)


def _weekly_planner(canvas: Canvas, palette: dict, header_text: str) -> None:
    margin = int(canvas.w * 0.06)
    top = _header(canvas, palette, header_text, margin)
    line_color = palette["accent"][-1]
    label_font = ImageFont.truetype(resolve_font("sans_bold"), int(canvas.w * 0.026))

    col_w = (canvas.w - 2 * margin) / len(DAYS)
    col_top = top + int(canvas.h * 0.015)
    col_bottom = canvas.h - margin - int(canvas.h * 0.1)
    header_h = label_font.size * 1.8

    for i, day in enumerate(DAYS):
        x = margin + i * col_w
        canvas.draw.text((x + col_w * 0.08, col_top), day, font=label_font, fill=palette["ink"])
        canvas.draw.line([(x, col_top), (x, col_bottom)], fill=line_color, width=2)
        n_lines = 9
        for li in range(1, n_lines + 1):
            ly = col_top + header_h + li * (col_bottom - col_top - header_h) / n_lines
            canvas.draw.line([(x + col_w * 0.08, ly), (x + col_w * 0.92, ly)], fill=line_color, width=1)
    canvas.draw.line([(canvas.w - margin, col_top), (canvas.w - margin, col_bottom)], fill=line_color, width=2)

    notes_top = col_bottom + int(canvas.h * 0.025)
    notes_font = ImageFont.truetype(resolve_font("sans_bold"), int(canvas.w * 0.026))
    canvas.draw.text((margin, notes_top), "TOP PRIORITIES", font=notes_font, fill=palette["ink"])
    for i in range(3):
        cy = notes_top + int(canvas.h * 0.035) + i * int(canvas.h * 0.022)
        r = int(canvas.w * 0.007)
        canvas.draw.ellipse([margin, cy, margin + 2 * r, cy + 2 * r], outline=palette["ink"], width=2)
        canvas.draw.line([(margin + 3 * r, cy + r), (canvas.w - margin, cy + r)], fill=line_color, width=1)


def _weekly_grid_content(canvas: Canvas, palette: dict, header_text: str) -> None:
    """The write-in week grid only (title, MONTH/WEEK fields, a 3x3 box
    of day cells with Sunday + Notes sharing the bottom row - matches the
    layout of well-performing competitor weekly planners), sized to fill
    whatever canvas it's given. Used both by _weekly_planner (on its own
    plain white page) and render_weekly_grid_rgba (composited into an
    illustrated background's safe zone)."""
    margin = int(canvas.w * 0.06)
    line_color = palette["accent"][-1]
    title_font = ImageFont.truetype(resolve_font("serif_bold"), int(canvas.w * 0.09))
    field_font = ImageFont.truetype(resolve_font("sans_bold"), int(canvas.w * 0.032))
    label_font = ImageFont.truetype(resolve_font("sans_bold"), int(canvas.w * 0.034))

    # Extra clearance above the title, beyond the plain margin: a
    # composited illustrated background's corner art (e.g. a witch hat
    # tilted into the top-left) can dip below the detected blank-box
    # edge without crossing its center row/column, so centerline-based
    # safe-zone detection (_detect_safe_zone) won't catch it - found via
    # a real title/hat collision on the Halloween weekly planner. This
    # keeps the title clear of that kind of corner bleed regardless.
    top = margin + int(canvas.h * 0.09)
    bbox = canvas.draw.textbbox((0, 0), header_text.upper(), font=title_font)
    canvas.draw.text((canvas.w / 2, top), header_text.upper(), font=title_font, fill=palette["ink"], anchor="ma")
    top += (bbox[3] - bbox[1]) + int(canvas.h * 0.03)

    canvas.draw.text((margin, top), "MONTH:", font=field_font, fill=palette["ink"])
    canvas.draw.line(
        [(margin + field_font.size * 3.2, top + field_font.size * 0.85), (canvas.w * 0.52, top + field_font.size * 0.85)],
        fill=line_color, width=2,
    )
    canvas.draw.text((canvas.w * 0.56, top), "WEEK:", font=field_font, fill=palette["ink"])
    canvas.draw.line(
        [(canvas.w * 0.56 + field_font.size * 2.8, top + field_font.size * 0.85), (canvas.w - margin, top + field_font.size * 0.85)],
        fill=line_color, width=2,
    )
    top += int(canvas.h * 0.06)

    grid_bottom = canvas.h - margin
    n_cols, n_rows = 3, 3
    col_w = (canvas.w - 2 * margin) / n_cols
    row_h = (grid_bottom - top) / n_rows
    gap = min(col_w, row_h) * 0.06

    day_layout = [
        ["MON", "TUE", "WED"],
        ["THU", "FRI", "SAT"],
        ["SUN", None, None],
    ]

    def cell_box(r: int, c: int, span: int = 1) -> tuple[float, float, float, float]:
        x0 = margin + c * col_w + gap
        y0 = top + r * row_h + gap
        x1 = margin + (c + span) * col_w - gap
        y1 = top + (r + 1) * row_h - gap
        return x0, y0, x1, y1

    for r, row in enumerate(day_layout):
        c = 0
        while c < n_cols:
            label = row[c]
            if label is None:
                c += 1
                continue
            x0, y0, x1, y1 = cell_box(r, c)
            canvas.draw.rectangle([x0, y0, x1, y1], outline=line_color, width=2)
            canvas.draw.text((x0 + gap, y0 + gap * 0.6), label, font=label_font, fill=palette["ink"])
            for li in range(1, 6):
                ly = y0 + (y1 - y0) * (0.32 + li * 0.12)
                if ly < y1 - gap:
                    canvas.draw.line([(x0 + gap, ly), (x1 - gap, ly)], fill=line_color, width=1)
            c += 1

    notes_x0, notes_y0, notes_x1, notes_y1 = cell_box(2, 1, span=2)
    canvas.draw.rectangle([notes_x0, notes_y0, notes_x1, notes_y1], outline=line_color, width=2)
    canvas.draw.text((notes_x0 + gap, notes_y0 + gap * 0.6), "NOTES", font=label_font, fill=palette["ink"])
    for li in range(1, 6):
        ly = notes_y0 + (notes_y1 - notes_y0) * (0.32 + li * 0.12)
        if ly < notes_y1 - gap:
            canvas.draw.line([(notes_x0 + gap, ly), (notes_x1 - gap, ly)], fill=line_color, width=1)


def render_weekly_grid_rgba(size: tuple[int, int], header_text: str, palette_name: str) -> "Canvas":
    """The weekly grid rendered on a transparent canvas, for compositing
    into a safe-zone box of an externally illustrated background - same
    pattern as render_calendar_grid_rgba."""
    palette = get_palette(palette_name)
    canvas = Canvas.transparent(size)
    _weekly_grid_content(canvas, palette, header_text)
    return canvas


def _budget_tracker(canvas: Canvas, palette: dict, header_text: str) -> None:
    margin = int(canvas.w * 0.09)
    top = _header(canvas, palette, header_text, margin)
    label_font = ImageFont.truetype(resolve_font("sans_bold"), int(canvas.w * 0.028))
    section_font = ImageFont.truetype(resolve_font("serif_bold"), int(canvas.w * 0.03))
    line_color = palette["accent"][-1]
    amount_x = canvas.w * 0.7

    y = top + int(canvas.h * 0.015)
    n_rows = len(BUDGET_CATEGORIES) + 5
    row_h = (canvas.h - margin - y) / n_rows

    def row(text: str, bold: bool = False, rule: bool = True) -> None:
        nonlocal y
        font = section_font if bold else label_font
        canvas.draw.text((margin, y), text, font=font, fill=palette["ink"])
        if rule:
            line_y = y + font.size * 0.85
            canvas.draw.line([(amount_x, line_y), (canvas.w - margin, line_y)], fill=line_color, width=1)
        y += row_h

    row("MONTHLY INCOME", bold=True)
    row("Total Income")
    y += row_h * 0.4
    row("EXPENSES", bold=True, rule=False)
    for cat in BUDGET_CATEGORIES:
        row(cat)
    y += row_h * 0.15
    canvas.draw.line([(margin, y), (canvas.w - margin, y)], fill=palette["ink"], width=max(2, int(canvas.w * 0.0025)))
    y += row_h * 0.35
    row("Total Expenses", bold=True)
    row("Remaining / Saved", bold=True)


def _habit_tracker(canvas: Canvas, palette: dict, header_text: str) -> None:
    margin = int(canvas.w * 0.08)
    top = _header(canvas, palette, header_text, margin)
    n_habits, n_days = 10, 31
    line_color = palette["accent"][-1]

    grid_left = margin + int(canvas.w * 0.24)
    grid_right = canvas.w - margin
    grid_top = top + int(canvas.h * 0.03)
    grid_bottom = canvas.h - margin
    row_h = (grid_bottom - grid_top) / n_habits
    col_w = (grid_right - grid_left) / n_days

    for r in range(n_habits + 1):
        y = grid_top + r * row_h
        canvas.draw.line([(margin, y), (grid_right, y)], fill=line_color, width=1)
    for c in range(n_days + 1):
        x = grid_left + c * col_w
        canvas.draw.line([(x, grid_top), (x, grid_bottom)], fill=line_color, width=1)

    tiny_font = ImageFont.truetype(resolve_font("sans"), max(10, int(col_w * 0.55)))
    for d in range(1, n_days + 1, 5):
        x = grid_left + (d - 0.5) * col_w
        canvas.draw.text((x, grid_top - tiny_font.size * 1.5), str(d), font=tiny_font, fill=palette["ink"], anchor="mm")

    for r in range(n_habits):
        y = grid_top + (r + 0.62) * row_h
        canvas.draw.line([(margin, y), (grid_left - int(canvas.w * 0.015), y)], fill=line_color, width=1)


def _checklist(canvas: Canvas, palette: dict, header_text: str) -> None:
    margin = int(canvas.w * 0.1)
    top = _header(canvas, palette, header_text, margin)
    n_items, cols = 20, 2
    items_per_col = n_items // cols
    col_w = (canvas.w - 2 * margin) / cols
    row_h = (canvas.h - margin - top) / (items_per_col + 1)
    box = int(canvas.w * 0.02)

    for c in range(cols):
        for r in range(items_per_col):
            x = margin + c * col_w
            y = top + int(canvas.h * 0.02) + r * row_h
            canvas.draw.rectangle([x, y, x + box, y + box], outline=palette["ink"], width=2)
            canvas.draw.line(
                [(x + box * 1.8, y + box * 0.5), (x + col_w - int(canvas.w * 0.02), y + box * 0.5)],
                fill=palette["accent"][-1],
                width=1,
            )


def _monthly_calendar(
    canvas: Canvas,
    palette: dict,
    header_text: str,
    month: int | None = None,
    year: int | None = None,
    undated: bool = False,
    accent_motifs: tuple[str, ...] = ("pumpkin", "bat", "ghost", "leaf"),
) -> None:
    margin = int(canvas.w * 0.07)
    top = _header(canvas, palette, header_text, margin)
    line_color = palette["accent"][-1]
    label_font = ImageFont.truetype(resolve_font("sans_bold"), int(canvas.w * 0.026))
    date_font = ImageFont.truetype(resolve_font("sans_bold"), int(canvas.w * 0.026))

    n_cols, n_rows = 7, 6
    grid_top = top + int(canvas.h * 0.02)
    grid_bottom = canvas.h - margin
    col_w = (canvas.w - 2 * margin) / n_cols
    header_row_h = label_font.size * 1.8
    body_top = grid_top + header_row_h
    row_h = (grid_bottom - body_top) / n_rows

    for i, day in enumerate(CALENDAR_DAYS):
        x = margin + i * col_w
        canvas.draw.text(
            (x + col_w / 2, grid_top + header_row_h / 2), day, font=label_font, fill=palette["ink"], anchor="mm"
        )

    for r in range(n_rows + 1):
        y = body_top + r * row_h
        canvas.draw.line([(margin, y), (canvas.w - margin, y)], fill=line_color, width=1)
    for c in range(n_cols + 1):
        x = margin + c * col_w
        canvas.draw.line([(x, grid_top), (x, grid_bottom)], fill=line_color, width=1)
    canvas.draw.line([(margin, grid_top), (canvas.w - margin, grid_top)], fill=palette["ink"], width=2)
    canvas.draw.line([(margin, body_top), (canvas.w - margin, body_top)], fill=palette["ink"], width=2)

    used_cells: set[tuple[int, int]] = set()
    if not undated:
        if month is None or year is None:
            raise ValueError("monthly_calendar requires month and year unless undated=True")
        first_weekday, days_in_month = _calendar.monthrange(year, month)  # Mon=0 .. Sun=6
        start_col = (first_weekday + 1) % 7  # convert to Sun=0 .. Sat=6
        day_num = 1
        for r in range(n_rows):
            for c in range(n_cols):
                if (r == 0 and c < start_col) or day_num > days_in_month:
                    continue
                x = margin + c * col_w + col_w * 0.08
                y = body_top + r * row_h + row_h * 0.06
                canvas.draw.text((x, y), str(day_num), font=date_font, fill=palette["ink"])
                used_cells.add((r, c))
                day_num += 1

    icon_r = min(col_w, row_h) * 0.16
    empty_cells = [(r, c) for r in range(n_rows) for c in range(n_cols) if (r, c) not in used_cells]
    for i, motif in enumerate(accent_motifs):
        if i >= len(empty_cells):
            break
        r, c = empty_cells[(i * 7) % len(empty_cells)]
        cx = margin + (c + 0.82) * col_w
        cy = body_top + (r + 0.78) * row_h
        # Always the first accent color, not cycled through all of them -
        # some palettes' later accent entries are near-white/cream and
        # nearly invisible against this template's light page background.
        draw_icon(canvas.draw, motif, cx, cy, icon_r, palette["accent"][0])


def render_calendar_grid_rgba(
    size: tuple[int, int],
    header_text: str,
    palette_name: str,
    month: int | None = None,
    year: int | None = None,
    undated: bool = False,
) -> "Canvas":
    """monthly_calendar rendered on a transparent canvas at `size`, for
    compositing into a safe-zone box of an externally illustrated
    background (see pipeline/canva_import.py's calendar-background
    workflow) instead of onto _monthly_calendar's own plain white page.

    No accent icons in empty cells here (accent_motifs=()) - the
    illustrated Canva background already carries the design; small icons
    scattered inside the plain grid area read as clutter/mistakes rather
    than decoration once there's a bold illustrated border above it."""
    palette = get_palette(palette_name)
    canvas = Canvas.transparent(size)
    _monthly_calendar(canvas, palette, header_text, month=month, year=year, undated=undated, accent_motifs=())
    return canvas


def _tint(hex_color: str, factor: float) -> tuple[int, int, int]:
    """Blend `hex_color` toward white by `factor` (0 = original, 1 = white)."""
    r, g, b = ImageColor.getrgb(hex_color)
    return (int(r + (255 - r) * factor), int(g + (255 - g) * factor), int(b + (255 - b) * factor))


def _shade(hex_color: str, factor: float) -> tuple[int, int, int]:
    """Blend `hex_color` toward black by `factor` (0 = original, 1 = black)."""
    r, g, b = ImageColor.getrgb(hex_color)
    return (int(r * (1 - factor)), int(g * (1 - factor)), int(b * (1 - factor)))


def _mood_colors(palette: dict) -> list[tuple[int, int, int]]:
    """An 8-shade ramp (best to worst mood) built from the palette's own
    accent/ink colors, instead of a fixed mood-color list - keeps every
    mood tracker variant on-palette rather than reusing the same 8 hues
    across every color scheme."""
    a0, a1, a2 = palette["accent"][0], palette["accent"][1], palette["accent"][2]
    return [
        _tint(a0, 0.0),
        _tint(a1, 0.0),
        _tint(a2, 0.0),
        _tint(a0, 0.5),
        _tint(a1, 0.55),
        _tint(a2, 0.6),
        _shade(palette["ink"], 0.35),
        _shade(palette["ink"], 0.7),
    ]


CREAM_PAGE_BG = (0xF6, 0xEC, 0xDA)
_STEAM_GREEN = (0x8F, 0xAE, 0x6B)


def _fill_page(canvas: Canvas, color) -> None:
    """Paint the whole canvas a solid color - used by the illustrated-
    parchment templates to override the shared white PAGE_BG."""
    canvas.draw.rectangle([0, 0, canvas.w, canvas.h], fill=color)


def _dotted_line(draw, x0: float, x1: float, y: float, fill, dot: float = 3, gap: float = 3.5) -> None:
    x = x0
    while x < x1:
        x_end = min(x + dot, x1)
        draw.line([(x, y), (x_end, y)], fill=fill, width=1)
        x += dot + gap


def _mini_star(draw, cx: float, cy: float, r: float, fill) -> None:
    points = []
    for i in range(8):
        angle = math.pi / 4 * i - math.pi / 2
        radius = r if i % 2 == 0 else r * 0.42
        points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    draw.polygon(points, fill=fill)


def _mini_heart(draw, cx: float, cy: float, r: float, fill) -> None:
    lobe_r = r * 0.42
    ldx = lobe_r * 0.6
    ly = cy - lobe_r * 0.25
    draw.ellipse([cx - ldx - lobe_r, ly - lobe_r, cx - ldx + lobe_r, ly + lobe_r], fill=fill)
    draw.ellipse([cx + ldx - lobe_r, ly - lobe_r, cx + ldx + lobe_r, ly + lobe_r], fill=fill)
    draw.polygon([(cx - lobe_r * 1.7, cy - lobe_r * 0.1), (cx + lobe_r * 1.7, cy - lobe_r * 0.1), (cx, cy + r * 0.9)], fill=fill)


def _mood_glyph(draw, name: str, cx: float, cy: float, r: float, color) -> None:
    """A tiny glyph inside a mood-key swatch dot - matches the reference
    mood tracker's icon-in-circle key (star/heart/sun/leaf/cloud/bolt/
    spiral/skull) instead of a plain color dot."""
    if name == "star":
        _mini_star(draw, cx, cy, r * 0.9, color)
    elif name == "heart":
        _mini_heart(draw, cx, cy, r * 0.85, color)
    elif name == "sun":
        draw.ellipse([cx - r * 0.4, cy - r * 0.4, cx + r * 0.4, cy + r * 0.4], fill=color)
        for i in range(8):
            ang = i * math.pi / 4
            x0, y0 = cx + math.cos(ang) * r * 0.55, cy + math.sin(ang) * r * 0.55
            x1, y1 = cx + math.cos(ang) * r * 0.82, cy + math.sin(ang) * r * 0.82
            draw.line([(x0, y0), (x1, y1)], fill=color, width=1)
    elif name == "leaf":
        draw.polygon([(cx, cy - r * 0.7), (cx + r * 0.5, cy), (cx, cy + r * 0.7), (cx - r * 0.5, cy)], fill=color)
        draw.line([(cx, cy - r * 0.6), (cx, cy + r * 0.6)], fill=_shade(color, 0.25) if isinstance(color, str) else color, width=1)
    elif name == "cloud":
        for dx, dy, rr in [(-r * 0.32, r * 0.12, r * 0.32), (r * 0.05, -r * 0.05, r * 0.4), (r * 0.38, r * 0.14, r * 0.28)]:
            draw.ellipse([cx + dx - rr, cy + dy - rr, cx + dx + rr, cy + dy + rr], fill=color)
    elif name == "bolt":
        draw.polygon(
            [
                (cx + r * 0.1, cy - r * 0.8), (cx - r * 0.35, cy + r * 0.05), (cx - r * 0.05, cy + r * 0.05),
                (cx - r * 0.15, cy + r * 0.8), (cx + r * 0.4, cy - r * 0.1), (cx + r * 0.05, cy - r * 0.1),
            ],
            fill=color,
        )
    elif name == "spiral":
        pts = []
        for i in range(20):
            t = i / 19
            ang = t * 2.6 * math.pi
            rad = r * 0.12 + t * r * 0.55
            pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
        draw.line(pts, fill=color, width=2)
    elif name == "skull":
        draw.ellipse([cx - r * 0.42, cy - r * 0.48, cx + r * 0.42, cy + r * 0.2], fill=color)
        draw.rectangle([cx - r * 0.28, cy, cx + r * 0.28, cy + r * 0.35], fill=color)


def _draw_candle(draw, cx: float, cy: float, w: float, h: float, ink, flame_color) -> None:
    draw.rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], fill=ink)
    draw.ellipse([cx - w * 0.75, cy - h / 2 - w * 0.15, cx + w * 0.75, cy - h / 2 + w * 0.15], fill=ink)
    flame_w, flame_h = w * 1.3, h * 0.35
    fy = cy - h / 2 - w * 0.15
    draw.polygon(
        [(cx, fy - flame_h), (cx + flame_w / 2, fy - flame_h * 0.15), (cx, fy + flame_h * 0.1), (cx - flame_w / 2, fy - flame_h * 0.15)],
        fill=flame_color,
    )


def _draw_potion(draw, cx: float, cy: float, w: float, h: float, ink, liquid) -> None:
    neck_w, neck_h = w * 0.32, h * 0.22
    draw.rectangle([cx - neck_w / 2, cy - h / 2, cx + neck_w / 2, cy - h / 2 + neck_h], outline=ink, width=2)
    draw.ellipse([cx - neck_w * 0.7, cy - h / 2 - neck_h * 0.4, cx + neck_w * 0.7, cy - h / 2 + neck_h * 0.3], fill=ink)
    body_top = cy - h / 2 + neck_h
    draw.rounded_rectangle([cx - w / 2, body_top, cx + w / 2, cy + h / 2], radius=w * 0.3, outline=ink, width=2)
    draw.rounded_rectangle(
        [cx - w / 2 + 2, body_top + (cy + h / 2 - body_top) * 0.35, cx + w / 2 - 2, cy + h / 2 - 2],
        radius=w * 0.25, fill=liquid,
    )


def _draw_mini_cauldron_scene(draw, cx: float, cy: float, r: float, ink) -> None:
    """A tiny cauldron-with-ghosts vignette (the Sunday cell's corner
    illustration on the weekly to-do list) - separate from the big
    mood-tracker cauldron so its size/detail level fits a small cell."""
    pot_rx, pot_ry = r * 0.85, r * 0.55
    draw.ellipse([cx - pot_rx, cy - pot_ry, cx + pot_rx, cy + pot_ry], fill=ink)
    leg_len = r * 0.22
    for side in (-1, 0, 1):
        lx = cx + side * pot_rx * 0.55
        draw.line([(lx, cy + pot_ry * 0.95), (lx - leg_len * 0.4, cy + pot_ry * 0.95 + leg_len)], fill=ink, width=2)
        draw.line([(lx, cy + pot_ry * 0.95), (lx + leg_len * 0.4, cy + pot_ry * 0.95 + leg_len)], fill=ink, width=2)
    draw_icon(draw, "ghost", cx - pot_rx * 0.7, cy - pot_ry * 1.6, r * 0.32, "#FFFFFF")
    draw_icon(draw, "ghost", cx + pot_rx * 0.75, cy - pot_ry * 1.9, r * 0.24, "#FFFFFF")


def _spiderweb(draw, cx: float, cy: float, r: float, color) -> None:
    for i in range(5):
        ang = math.pi / 2 * (i / 4)
        draw.line([(cx, cy), (cx + math.cos(ang) * r, cy - math.sin(ang) * r)], fill=color, width=1)
    for frac in (0.4, 0.7, 1.0):
        pts = []
        for i in range(6):
            ang = math.pi / 2 * (i / 5)
            pts.append((cx + math.cos(ang) * r * frac, cy - math.sin(ang) * r * frac))
        draw.line(pts, fill=color, width=1)


def _mood_tracker(canvas: Canvas, palette: dict, header_text: str) -> None:
    """A month-at-a-glance mood tracker: a numbered day grid inside a
    hand-drawn-style cauldron outline, with a color-coded mood key
    beside it. Modeled closely on the trending "cauldron mood tracker"
    printable format the user pointed to - own art (ink line-work, no
    traced/borrowed illustration) and own copy (no third-party movie
    title or character silhouettes), but deliberately the same overall
    look rather than a from-scratch reinterpretation."""
    _fill_page(canvas, CREAM_PAGE_BG)
    margin = int(canvas.w * 0.07)
    top = _header(canvas, palette, header_text, margin)
    line_color = palette["accent"][-1]

    subtitle_font = ImageFont.truetype(resolve_font("sans_bold"), int(canvas.w * 0.026))
    canvas.draw.text(
        (canvas.w / 2, top), "TRACK YOUR MOOD EACH DAY", font=subtitle_font, fill=palette["accent"][0], anchor="ma"
    )
    top += int(canvas.h * 0.05)

    deco_w = canvas.w * 0.1
    key_w = canvas.w * 0.28
    pot_area_x0 = margin + deco_w
    pot_area_x1 = canvas.w - margin - key_w
    pot_cx = (pot_area_x0 + pot_area_x1) / 2
    area_top = top + int(canvas.h * 0.035)
    area_bottom = canvas.h - margin - int(canvas.h * 0.09)

    pot_w = (pot_area_x1 - pot_area_x0) * 0.94
    pot_h = (area_bottom - area_top) * 0.8
    pot_r = min(pot_w, pot_h) / 2
    line_w = max(3, int(canvas.w * 0.0045))

    # A single rounded body outline capped by a flatter rim ellipse right
    # at its shoulder - reads as "pot with a lip", closer to the
    # reference's hand-drawn cauldron than a distinct neck/handle
    # assembly. No handles (the reference doesn't have them either).
    body_rx = pot_r * 0.98
    body_ry = pot_r * 0.92
    body_cy = area_top + body_ry + int(canvas.h * 0.05)
    # Position the rim where the body already has real width (not at its
    # polar tip, which is a single point) so the rim's ends land ON the
    # body's curve instead of floating above it with a gap - an ellipse
    # outline only touches its own pole at one point, so anchoring the
    # rim there (as an earlier version did) left a visible gap all the
    # way round before the two curves met.
    rim_frac = 0.82
    rim_cy = body_cy - body_ry * rim_frac
    rim_rx = body_rx * math.sqrt(1 - rim_frac**2) * 1.06
    rim_ry = pot_r * 0.11

    # green swirly steam above the rim
    for dx in (-pot_r * 0.4, -pot_r * 0.05, pot_r * 0.35):
        sx = pot_cx + dx
        sy = rim_cy - rim_ry - int(canvas.h * 0.005)
        pts = [(sx, sy)]
        for seg in range(1, 4):
            ang = seg * 2.2
            wob = math.sin(ang) * pot_r * 0.09
            ny = sy - seg * canvas.h * 0.014
            pts.append((sx + wob, ny))
        canvas.draw.line(pts, fill=_STEAM_GREEN, width=3, joint="curve")

    # tripod: small curled/hooked feet rather than straight angular legs
    foot_r = pot_r * 0.11
    for side in (-1, 0, 1):
        fx = pot_cx + side * body_rx * 0.55
        fy = body_cy + body_ry * 0.97
        canvas.draw.arc(
            [fx - foot_r, fy - foot_r * 0.3, fx + foot_r, fy + foot_r * 1.5], start=200, end=520, fill=palette["ink"], width=line_w,
        )

    canvas.draw.ellipse(
        [pot_cx - body_rx, body_cy - body_ry, pot_cx + body_rx, body_cy + body_ry],
        outline=palette["ink"], width=line_w,
    )
    canvas.draw.ellipse(
        [pot_cx - rim_rx, rim_cy - rim_ry, pot_cx + rim_rx, rim_cy + rim_ry],
        outline=palette["ink"], width=line_w,
    )

    # numbered day grid, straight on the parchment inside the pot outline
    n_days, cols, rows = 31, 7, 5
    grid_w = pot_r * 1.28
    grid_h = grid_w * rows / cols
    gx0 = pot_cx - grid_w / 2
    gy0 = body_cy - grid_h / 2 + pot_r * 0.08
    cell_w, cell_h = grid_w / cols, grid_h / rows
    circle_r = min(cell_w, cell_h) * 0.36
    num_font = ImageFont.truetype(resolve_font("sans_bold"), max(10, int(cell_h * 0.32)))
    n = 1
    for r in range(rows):
        for c in range(cols):
            if n > n_days:
                break
            ccx, ccy = gx0 + (c + 0.5) * cell_w, gy0 + (r + 0.5) * cell_h
            canvas.draw.ellipse(
                [ccx - circle_r, ccy - circle_r, ccx + circle_r, ccy + circle_r], outline=line_color, width=2
            )
            canvas.draw.text((ccx, ccy), str(n), font=num_font, fill=palette["ink"], anchor="mm")
            n += 1

    # side decorations: candle + cat on the left, potion on the right,
    # echoing the reference's witchy still-life props
    deco_cx = margin + deco_w * 0.5
    _draw_candle(canvas.draw, deco_cx, body_cy - body_ry * 0.3, deco_w * 0.22, deco_w * 0.55, palette["ink"], "#F2A65A")
    draw_icon(canvas.draw, "black_cat", deco_cx, body_cy + body_ry * 0.35, deco_w * 0.42, palette["ink"])
    _spiderweb(canvas.draw, margin + deco_w * 0.35, area_top + int(canvas.h * 0.01), deco_w * 0.6, palette["ink"])

    potion_cx = canvas.w - margin - key_w * 0.35
    _draw_potion(canvas.draw, potion_cx, area_top + int(canvas.h * 0.02), deco_w * 0.4, deco_w * 0.65, palette["ink"], palette["accent"][1])

    # mood key
    key_x0 = canvas.w - margin - key_w + int(canvas.w * 0.02)
    key_title_font = ImageFont.truetype(resolve_font("serif_bold"), int(canvas.w * 0.03))
    key_font = ImageFont.truetype(resolve_font("sans_bold"), int(canvas.w * 0.02))
    key_top0 = area_top + int(canvas.h * 0.09)
    canvas.draw.text((key_x0, key_top0), "MOOD KEY", font=key_title_font, fill=palette["ink"])

    labels = ["Amazing", "Happy", "Calm", "Okay", "Sad", "Stressed", "Anxious", "Awful"]
    glyphs = ["star", "heart", "sun", "leaf", "cloud", "bolt", "spiral", "skull"]
    colors = _mood_colors(palette)
    key_top = key_top0 + int(canvas.h * 0.05)
    row_h = (area_bottom - key_top) / len(labels)
    swatch_r = int(canvas.w * 0.013)
    for i, (label, glyph, color) in enumerate(zip(labels, glyphs, colors)):
        cy = key_top + i * row_h + swatch_r
        canvas.draw.ellipse([key_x0, cy - swatch_r, key_x0 + 2 * swatch_r, cy + swatch_r], fill=color)
        glyph_color = "#FFFFFF" if sum(color) < 380 else _shade(palette["ink"], 0.0)
        _mood_glyph(canvas.draw, glyph, key_x0 + swatch_r, cy, swatch_r * 0.7, glyph_color)
        canvas.draw.text(
            (key_x0 + swatch_r * 2.6, cy), label.upper(), font=key_font, fill=palette["ink"], anchor="lm"
        )

    banner_font = ImageFont.truetype(resolve_font("serif_bold"), int(canvas.w * 0.032))
    banner_text = "MAGIC IN PROGRESS"
    bbox = canvas.draw.textbbox((0, 0), banner_text, font=banner_font)
    bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = int(canvas.w * 0.025)
    bx0, bx1 = canvas.w / 2 - bw / 2 - pad, canvas.w / 2 + bw / 2 + pad
    by0 = area_bottom + int(canvas.h * 0.025)
    by1 = by0 + bh + pad
    notch = pad * 0.6
    canvas.draw.polygon(
        [
            (bx0, by0), (bx1, by0), (bx1 - notch, (by0 + by1) / 2),
            (bx1, by1), (bx0, by1), (bx0 + notch, (by0 + by1) / 2),
        ],
        outline=palette["ink"], width=2,
    )
    canvas.draw.text((canvas.w / 2, (by0 + by1) / 2), banner_text, font=banner_font, fill=palette["ink"], anchor="mm")


def _weekly_todo(canvas: Canvas, palette: dict, header_text: str) -> None:
    """A cream-parchment weekly to-do list: an illustrated header cluster
    (mug, pumpkins, ghost, book stack) over a 3x2+Sunday/Self-Care grid
    of cards, each with a small tab-style day badge, heart checkboxes,
    and dotted lines - modeled closely on the trending illustrated
    weekly-checklist format the user pointed to (own art/copy, same
    overall structure and feel)."""
    _fill_page(canvas, CREAM_PAGE_BG)
    margin = int(canvas.w * 0.06)

    title_top = margin + int(canvas.h * 0.01)
    script_font = ImageFont.truetype(resolve_font("serif_italic"), int(canvas.w * 0.09))
    caps_font = ImageFont.truetype(resolve_font("serif_bold"), int(canvas.w * 0.065))
    canvas.draw.text((canvas.w / 2, title_top), "Weekly", font=script_font, fill=palette["ink"], anchor="ma")
    bbox = canvas.draw.textbbox((0, 0), "Weekly", font=script_font)
    title_top += (bbox[3] - bbox[1]) + int(canvas.h * 0.005)
    canvas.draw.text((canvas.w / 2, title_top), "TO-DO LIST", font=caps_font, fill=palette["ink"], anchor="ma")
    bbox2 = canvas.draw.textbbox((0, 0), "TO-DO LIST", font=caps_font)
    title_top += (bbox2[3] - bbox2[1]) + int(canvas.h * 0.012)

    subtitle_font = ImageFont.truetype(resolve_font("sans_bold"), int(canvas.w * 0.024))
    canvas.draw.text((canvas.w / 2, title_top), "HAPPY SPOOKY SEASON", font=subtitle_font, fill=palette["accent"][0], anchor="ma")
    bbox3 = canvas.draw.textbbox((0, 0), "HAPPY SPOOKY SEASON", font=subtitle_font)
    top = title_top + (bbox3[3] - bbox3[1]) + int(canvas.h * 0.025)

    # header cluster flanking the title: a mug on the left, a small book
    # stack on the right, each with a pumpkin/ghost accent
    deco_r = canvas.w * 0.028
    mug_cx, mug_cy = margin + deco_r * 1.8, margin + deco_r * 2.2
    canvas.draw.rounded_rectangle(
        [mug_cx - deco_r, mug_cy - deco_r, mug_cx + deco_r, mug_cy + deco_r * 1.1],
        radius=deco_r * 0.3, fill=palette["accent"][0], outline=palette["ink"], width=2,
    )
    canvas.draw.arc(
        [mug_cx + deco_r * 0.6, mug_cy - deco_r * 0.5, mug_cx + deco_r * 1.6, mug_cy + deco_r * 0.6],
        start=270, end=90, fill=palette["ink"], width=2,
    )
    canvas.draw.ellipse(
        [mug_cx - deco_r * 1.05, mug_cy - deco_r * 1.35, mug_cx + deco_r * 1.05, mug_cy - deco_r * 0.75], fill="#FFFFFF",
    )
    draw_icon(canvas.draw, "pumpkin", mug_cx + deco_r * 2.2, mug_cy + deco_r * 0.3, deco_r * 0.85, palette["ink"], palette["accent"][1])

    book_cx, book_cy = canvas.w - margin - deco_r * 2.2, margin + deco_r * 2.4
    for i, tint in enumerate((_tint(palette["accent"][1], 0.15), _tint(palette["accent"][2], 0.15))):
        bw, bh = deco_r * 2.6 - i * deco_r * 0.3, deco_r * 0.55
        by = book_cy + deco_r * 0.7 - i * bh
        canvas.draw.rectangle([book_cx - bw / 2, by - bh, book_cx + bw / 2, by], fill=tint, outline=palette["ink"], width=2)
    draw_icon(canvas.draw, "ghost", book_cx - deco_r * 1.8, book_cy - deco_r * 0.6, deco_r * 0.7, palette["ink"])
    draw_icon(canvas.draw, "pumpkin", book_cx, book_cy - deco_r * 1.3, deco_r * 0.75, palette["ink"], palette["accent"][1])

    grid_bottom = canvas.h - margin
    n_cols, n_rows = 3, 3
    col_w = (canvas.w - 2 * margin) / n_cols
    row_h = (grid_bottom - top) / n_rows
    gap = min(col_w, row_h) * 0.07

    day_layout = [["MONDAY", "TUESDAY", "WEDNESDAY"], ["THURSDAY", "FRIDAY", "SATURDAY"], ["SUNDAY", "SELF CARE", None]]
    card_fill = _tint(palette["accent"][0], 0.8)

    def cell_box(r: int, c: int) -> tuple[float, float, float, float]:
        x0 = margin + c * col_w + gap
        y0 = top + r * row_h + gap
        x1 = margin + (c + 1) * col_w - gap
        y1 = top + (r + 1) * row_h - gap
        return x0, y0, x1, y1

    for r, row in enumerate(day_layout):
        for c, label in enumerate(row):
            if label is None:
                continue
            x0, y0, x1, y1 = cell_box(r, c)
            canvas.draw.rounded_rectangle([x0, y0, x1, y1], radius=gap * 1.4, fill=card_fill, outline=palette["ink"], width=2)

            pill_h = (y1 - y0) * 0.15
            pill_w = (x1 - x0) * 0.66
            pill_y = y0 - pill_h * 0.15
            canvas.draw.rounded_rectangle(
                [x0 + gap * 0.3, pill_y, x0 + gap * 0.3 + pill_w, pill_y + pill_h],
                radius=pill_h * 0.45, fill=palette["accent"][0], outline=palette["ink"], width=2,
            )
            draw_icon(canvas.draw, "ghost", x0 + gap * 0.3 + pill_h * 0.55, pill_y + pill_h / 2, pill_h * 0.34, "#FFFFFF")
            label_font = ImageFont.truetype(resolve_font("sans_bold"), max(9, int(pill_h * 0.4)))
            canvas.draw.text(
                (x0 + gap * 0.3 + pill_h * 1.15, pill_y + pill_h / 2), label, font=label_font, fill=palette["ink"], anchor="lm"
            )

            n_lines = 5
            avail_top, avail_bottom = pill_y + pill_h + gap * 0.8, y1 - gap * 0.4
            check_r = min(col_w, row_h) * 0.045
            for li in range(n_lines):
                ly = avail_top + (li + 0.5) * (avail_bottom - avail_top) / n_lines
                _mini_heart(canvas.draw, x0 + gap * 0.6 + check_r, ly, check_r, palette["ink"])
                _dotted_line(canvas.draw, x0 + gap * 0.6 + check_r * 2.6, x1 - gap * 0.5, ly, palette["accent"][-1])

            if label == "SUNDAY":
                _draw_mini_cauldron_scene(canvas.draw, x1 - gap * 1.6, y1 - gap * 1.6, gap * 1.3, palette["ink"])
            else:
                icon_name = "pumpkin" if (r + c) % 2 == 0 else "ghost"
                draw_icon(canvas.draw, icon_name, x1 - gap * 1.3, y1 - gap * 1.3, gap * 1.0, palette["ink"], palette["accent"][1])


_TEMPLATE_FN = {
    "weekly_planner": _weekly_planner,
    "budget_tracker": _budget_tracker,
    "habit_tracker": _habit_tracker,
    "checklist": _checklist,
    "monthly_calendar": _monthly_calendar,
    "mood_tracker": _mood_tracker,
    "weekly_todo": _weekly_todo,
}


def generate(
    *,
    template: str,
    header: str,
    palette_name: str = "sage_minimal",
    size_name: str = "letter_8.5x11",
    seed: int | None = None,
    **template_kwargs,
) -> Canvas:
    if template not in _TEMPLATE_FN:
        raise ValueError(f"Unknown template '{template}'. Available: {', '.join(_TEMPLATE_FN)}")

    palette = get_palette(palette_name)
    size = size_px(size_name)
    canvas = Canvas(size, PAGE_BG)

    _TEMPLATE_FN[template](canvas, palette, header, **template_kwargs)
    return canvas
