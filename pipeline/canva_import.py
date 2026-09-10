"""Package a Canva-generated design into the same batch/metadata format
`pipeline.generate` produces, so it can be published with the existing
`pipeline.publish_digital` / `pipeline.publish_pod` scripts unchanged.

Canva generation itself is NOT scriptable from here - the Canva MCP tools
(generate-design, create-design-from-candidate, export-design) are only
callable interactively by Claude in a conversation, not from a standalone
Python process. The actual workflow is:

  1. In conversation, ask Claude to generate a design for a "canva" niche
     (see config/niches.yaml - each has a `prompts` list of {label, query}
     recipes and a `canva_design_type`). Claude calls generate-design,
     picks/creates a candidate design, and exports it as a PDF with NO
     forced paper size (`{"type": "pdf"}` - no `size` key). That matters:
     Canva's raw PNG export is capped at a modest width on the free plan
     (~1000-1500px failed with a generic "not allowed" error in testing),
     but PDF export renders the design at its own native canvas size -
     which for a "poster" design type is a full physical poster (huge,
     ~4960x7016px once rasterized at 300 DPI) regardless of plan.
  2. Claude runs this script with that one PDF export URL. It rasterizes
     the PDF locally at 300 DPI (via PyMuPDF) into one master image, then
     derives every size this niche needs (each `digital_sizes` /
     `pod_sizes` entry, using the same size table as every other
     generator - see design/engine.SIZES_IN) by center-cropping and
     resizing that master locally - no further Canva export calls needed.

Note: a design's native canvas size varies a lot by Canva design_type -
"poster" defaults to a large physical poster, "invitation" defaults to a
modest card size (which is *correct* for a card, not under-resolution;
300 DPI at invitation size is a few thousand pixels less than at poster
size because the invitation is physically smaller). Cropping a much
larger target out of a small native canvas will look soft - check that
a niche's `digital_sizes`/`pod_sizes` are a reasonable fit for the
`canva_design_type` before importing.

Usage:
    python -m pipeline.canva_import --niche halloween_vintage_apparel_canva \\
        --variant "Happy Haunting Pumpkin" \\
        --master-pdf <signed pdf export url, requested with no size param> \\
        --canva-design-id DAHUuBX0MfE --canva-edit-url https://www.canva.com/d/...
"""
from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

import pymupdf
import requests
from PIL import Image

from design.engine import size_px
from pipeline.generate import humanize, load_niches, render_seo, slugify

RASTER_DPI = 300


def _download(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    path.write_bytes(resp.content)


def _rasterize_master(pdf_path: Path) -> Image.Image:
    doc = pymupdf.open(pdf_path)
    pix = doc[0].get_pixmap(dpi=RASTER_DPI)
    mode = "RGBA" if pix.n >= 4 else "RGB"
    image = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
    return image.convert("RGB")


def _crop_to_ratio(master: Image.Image, target_w: int, target_h: int, anchor: float = 0.5) -> Image.Image:
    """Crop `master` to the target aspect ratio, then resize to the exact
    target pixel size. Right for a paper size a printable must fill edge
    to edge (letter, a4, 5x7, ...) - wrong for a POD print area whose
    ratio doesn't resemble the artwork's own (a tall poster cropped to a
    wide mug wrap keeps only a thin horizontal sliver, losing the title
    entirely) - use `_fit_within` for those instead.

    `anchor` (0-1) picks where along the cropped axis the slice is taken
    from - 0.5 (default) centers it, 0 takes the top/left edge, 1 the
    bottom/right. A tall portrait master cropped down to a short wide
    strip only shows ~1/3 of the original height, so if the composition's
    focal point isn't centered vertically, center-cropping can cut right
    through it - override anchor to keep the actual subject in frame."""
    src_ratio = master.width / master.height
    target_ratio = target_w / target_h
    if src_ratio > target_ratio:
        new_w = int(round(master.height * target_ratio))
        x0 = int(round((master.width - new_w) * anchor))
        cropped = master.crop((x0, 0, x0 + new_w, master.height))
    else:
        new_h = int(round(master.width / target_ratio))
        y0 = int(round((master.height - new_h) * anchor))
        cropped = master.crop((0, y0, master.width, y0 + new_h))
    return cropped.resize((target_w, target_h), Image.LANCZOS)


def _fit_within(master: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Scale `master` to fit entirely within (max_w, max_h), preserving
    its own aspect ratio - the whole graphic stays visible, sized for a
    print-on-demand product to center/scale within its print area (this
    is what a "box print" graphic on a t-shirt or mug actually is: the
    full rectangular design, not a crop of it)."""
    scale = min(max_w / master.width, max_h / master.height)
    new_size = (max(1, round(master.width * scale)), max(1, round(master.height * scale)))
    return master.resize(new_size, Image.LANCZOS)


def import_design(
    niche_name: str,
    variant: str,
    master_pdf_url: str,
    canva_design_id: str,
    canva_edit_url: str | None = None,
    out_dir: Path | None = None,
    price_override: float | None = None,
    pod_crop_anchor_override: float | None = None,
) -> dict:
    niches = load_niches()
    if niche_name not in niches:
        raise KeyError(f"Unknown niche '{niche_name}'. Available: {', '.join(sorted(niches))}")
    niche = niches[niche_name]
    if niche["type"] != "canva":
        raise ValueError(f"Niche '{niche_name}' is type '{niche['type']}', not 'canva'.")

    digital_sizes = niche.get("digital_sizes", [])
    pod_sizes = niche.get("pod_sizes", [])
    if not digital_sizes and not pod_sizes:
        raise ValueError(f"Niche '{niche_name}' has no digital_sizes or pod_sizes configured.")

    context = {"variant_title": humanize(variant), "quote": "", "quote_short": "", "motif_title": "", "text": ""}
    seo = render_seo(niche, context)

    out_dir = out_dir or Path("output") / niche_name
    design_slug = slugify(f"{niche_name}-{variant}-{uuid.uuid4().hex[:6]}")
    design_dir = out_dir / design_slug

    master_pdf_path = design_dir / "_master.pdf"
    _download(master_pdf_url, master_pdf_path)
    master = _rasterize_master(master_pdf_path)
    master_pdf_path.unlink()

    files: dict[str, dict[str, str]] = {}
    preview_path = design_dir / "preview.jpg"
    preview_size = (digital_sizes + pod_sizes)[0]

    for size_name in digital_sizes:
        w, h = size_px(size_name)
        derived = _crop_to_ratio(master, w, h)

        png_path = design_dir / f"{size_name}.png"
        derived.save(png_path, "PNG")
        files.setdefault("png", {})[size_name] = str(png_path)

        pdf_path = design_dir / f"{size_name}.pdf"
        derived.save(pdf_path, "PDF", resolution=RASTER_DPI)
        files.setdefault("pdf", {})[size_name] = str(pdf_path)

        if size_name == preview_size:
            preview = derived.copy()
            preview.thumbnail((1600, 1600))
            preview.save(preview_path, "JPEG", quality=87)

    pod_fit = niche.get("pod_fit", "contain")
    pod_crop_anchor = pod_crop_anchor_override if pod_crop_anchor_override is not None else niche.get("pod_crop_anchor", 0.5)
    for size_name in pod_sizes:
        w, h = size_px(size_name)
        derived = (
            _crop_to_ratio(master, w, h, anchor=pod_crop_anchor)
            if pod_fit == "cover"
            else _fit_within(master, w, h)
        )

        png_path = design_dir / f"{size_name}.png"
        derived.save(png_path, "PNG")
        files.setdefault("png", {})[size_name] = str(png_path)

        if size_name == preview_size:
            preview = derived.copy()
            preview.thumbnail((1600, 1600))
            preview.save(preview_path, "JPEG", quality=87)

    price_digital = niche.get("price_digital") if digital_sizes else None
    price_pod = niche.get("price_pod") if pod_sizes else None
    if price_override is not None:
        if digital_sizes:
            price_digital = price_override
        if pod_sizes:
            price_pod = price_override

    metadata = {
        "design_id": design_slug,
        "niche": niche_name,
        "product_mode": niche.get("product_mode", "digital"),
        "source": "canva",
        "canva_design_id": canva_design_id,
        "canva_edit_url": canva_edit_url,
        "variant": variant,
        "generator_type": "canva",
        "pod_fit": pod_fit,
        "title": seo["title"],
        "description": seo["description"],
        "tags": seo["tags"],
        "price_digital": price_digital,
        "price_pod": price_pod,
        "pod_sizes": pod_sizes,
        "digital_sizes": digital_sizes,
        "preview": str(preview_path),
        "files": files,
    }
    with open(design_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Package a Canva-generated design into the standard batch format.")
    parser.add_argument("--niche", required=True, help="Niche name from config/niches.yaml (must be type: canva)")
    parser.add_argument("--variant", required=True, help="Which niche 'prompts' label this design used (drives SEO title/description)")
    parser.add_argument("--master-pdf", required=True, help="Signed PDF export URL, requested with no 'size' param (see module docstring)")
    parser.add_argument("--canva-design-id", required=True, help="The Canva design ID (from create-design-from-candidate)")
    parser.add_argument("--canva-edit-url", default=None, help="The Canva edit URL, saved for reference/future edits")
    parser.add_argument("--out", default=None, help="Output directory (default: output/<niche>)")
    parser.add_argument("--price", type=float, default=None, help="Override the niche's default price_digital/price_pod")
    parser.add_argument(
        "--crop-anchor",
        type=float,
        default=None,
        help="0-1, where a pod_fit:cover crop is taken from along the cropped axis (0.5=center, default). "
        "Override when the composition's focal point isn't centered - see _crop_to_ratio docstring.",
    )
    args = parser.parse_args()

    out_dir = Path(args.out) if args.out else None

    metadata = import_design(
        args.niche,
        args.variant,
        args.master_pdf,
        args.canva_design_id,
        canva_edit_url=args.canva_edit_url,
        out_dir=out_dir,
        price_override=args.price,
        pod_crop_anchor_override=args.crop_anchor,
    )
    print(f"Imported {metadata['design_id']} -> {metadata['title'][:70]}")


if __name__ == "__main__":
    main()
