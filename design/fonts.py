"""Font resolution for the design generators.

No AI image generation is used anywhere in this repo (by request) - all
artwork is drawn procedurally with Pillow. Typography quality depends on
having decent fonts available, so this module resolves a small set of
named "roles" (serif, serif_bold, sans, sans_bold, script) to an actual
.ttf file on disk, in this order:

1. A custom font dropped in ``design/fonts/custom/<role>.ttf``. This is
   the easy way to upgrade the look later - grab a free, commercial-use
   font (e.g. Playfair Display, Cormorant, Montserrat from Google Fonts)
   and save it as e.g. ``design/fonts/custom/serif.ttf``.
2. Whatever fontconfig (``fc-match``) resolves on the current machine,
   tried against a list of common family names for that role.

This keeps the pipeline runnable out of the box on any Linux/Mac machine
with fontconfig installed (the default almost everywhere), with zero
network calls and zero paid services.
"""
from __future__ import annotations

import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

CUSTOM_FONT_DIR = Path(__file__).parent / "fonts" / "custom"

# Ordered fallback family names to try via fontconfig for each role.
FALLBACK_FAMILIES = {
    "serif": ["DejaVu Serif", "Liberation Serif", "FreeSerif", "Georgia", "Times New Roman"],
    "serif_bold": ["DejaVu Serif:bold", "Liberation Serif:bold", "FreeSerif:bold", "Georgia:bold"],
    "serif_italic": ["DejaVu Serif:italic", "Liberation Serif:italic", "FreeSerif:italic"],
    "sans": ["Liberation Sans", "DejaVu Sans", "FreeSans", "Helvetica", "Arial"],
    "sans_bold": ["Liberation Sans:bold", "DejaVu Sans:bold", "FreeSans:bold", "Helvetica:bold"],
    # No script/handwritten font ships with most base Linux installs.
    # Falls back to bold serif until a real script font is dropped in.
    "script": ["Liberation Serif:italic", "DejaVu Serif:italic", "FreeSerif:italic"],
}


class FontNotFoundError(RuntimeError):
    pass


@lru_cache(maxsize=None)
def _fc_match(family: str) -> str | None:
    if not shutil.which("fc-match"):
        return None
    try:
        result = subprocess.run(
            ["fc-match", "--format=%{file}", family],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except OSError:
        return None
    path = result.stdout.strip()
    return path or None


@lru_cache(maxsize=None)
def resolve_font(role: str) -> str:
    """Return an absolute path to a .ttf/.otf usable for the given role."""
    custom = CUSTOM_FONT_DIR / f"{role}.ttf"
    if custom.exists():
        return str(custom)

    for family in FALLBACK_FAMILIES.get(role, [role]):
        path = _fc_match(family)
        if path and Path(path).exists():
            return path

    raise FontNotFoundError(
        f"No font found for role '{role}'. Install fontconfig + a font, or drop a "
        f".ttf into design/fonts/custom/{role}.ttf"
    )
