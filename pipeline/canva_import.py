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
     picks/creates a candidate design, and exports it (PDF per size in
     `digital_sizes`, plus a PNG preview) via the Canva MCP tools.
  2. Claude then runs this script with the resulting export URLs (they're
     pre-signed and expire - typically within a few hours - so download
     promptly) to download the files and write metadata.json in the
     standard shape.

Usage:
    python -m pipeline.canva_import --niche halloween_vintage_posters_canva \\
        --variant "Happy Haunting Pumpkin" \\
        --pdf letter_8.5x11=<signed pdf url> a4=<signed pdf url> \\
        --preview <signed png url> \\
        --canva-design-id DAHUuBX0MfE --canva-edit-url https://www.canva.com/d/...
"""
from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

import requests

from pipeline.generate import humanize, load_niches, render_seo, slugify


def _download(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    path.write_bytes(resp.content)


def import_design(
    niche_name: str,
    variant: str,
    preview_url: str,
    canva_design_id: str,
    pdf_urls: dict[str, str] | None = None,
    png_urls: dict[str, str] | None = None,
    canva_edit_url: str | None = None,
    out_dir: Path | None = None,
    price_override: float | None = None,
) -> dict:
    pdf_urls = pdf_urls or {}
    png_urls = png_urls or {}
    if not pdf_urls and not png_urls:
        raise ValueError("Provide at least one of pdf_urls or png_urls.")

    niches = load_niches()
    if niche_name not in niches:
        raise KeyError(f"Unknown niche '{niche_name}'. Available: {', '.join(sorted(niches))}")
    niche = niches[niche_name]
    if niche["type"] != "canva":
        raise ValueError(f"Niche '{niche_name}' is type '{niche['type']}', not 'canva'.")

    context = {"variant_title": humanize(variant), "quote": "", "quote_short": "", "motif_title": "", "text": ""}
    seo = render_seo(niche, context)

    out_dir = out_dir or Path("output") / niche_name
    design_slug = slugify(f"{niche_name}-{variant}-{uuid.uuid4().hex[:6]}")
    design_dir = out_dir / design_slug

    files: dict[str, dict[str, str]] = {}
    for size_name, url in pdf_urls.items():
        pdf_path = design_dir / f"{size_name}.pdf"
        _download(url, pdf_path)
        files.setdefault("pdf", {})[size_name] = str(pdf_path)
    for size_name, url in png_urls.items():
        png_path = design_dir / f"{size_name}.png"
        _download(url, png_path)
        files.setdefault("png", {})[size_name] = str(png_path)

    preview_path = design_dir / "preview.jpg"
    downloaded_preview = design_dir / "preview_source.png"
    _download(preview_url, downloaded_preview)
    from PIL import Image

    Image.open(downloaded_preview).convert("RGB").save(preview_path, "JPEG", quality=87)
    downloaded_preview.unlink()

    price = price_override if price_override is not None else niche.get("price_digital")
    metadata = {
        "design_id": design_slug,
        "niche": niche_name,
        "product_mode": niche.get("product_mode", "digital"),
        "source": "canva",
        "canva_design_id": canva_design_id,
        "canva_edit_url": canva_edit_url,
        "variant": variant,
        "generator_type": "canva",
        "title": seo["title"],
        "description": seo["description"],
        "tags": seo["tags"],
        "price_digital": price,
        "price_pod": None,
        "pod_sizes": [],
        "digital_sizes": list(pdf_urls.keys()) + list(png_urls.keys()),
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
    parser.add_argument("--pdf", nargs="+", default=[], metavar="SIZE=URL", help="size=signed-pdf-url pairs, e.g. letter_8.5x11=https://... (use for designs whose native ratio matches a4/letter, like posters)")
    parser.add_argument("--png", nargs="+", default=[], metavar="SIZE=URL", help="size=signed-png-url pairs - use for designs with a non-paper aspect ratio, like invitations/cards, to avoid distorting them into a4/letter")
    parser.add_argument("--preview", required=True, help="Signed PNG export URL for the preview image")
    parser.add_argument("--canva-design-id", required=True, help="The Canva design ID (from create-design-from-candidate)")
    parser.add_argument("--canva-edit-url", default=None, help="The Canva edit URL, saved for reference/future edits")
    parser.add_argument("--out", default=None, help="Output directory (default: output/<niche>)")
    parser.add_argument("--price", type=float, default=None, help="Override the niche's default price_digital")
    args = parser.parse_args()

    pdf_urls = dict(pair.split("=", 1) for pair in args.pdf)
    png_urls = dict(pair.split("=", 1) for pair in args.png)
    out_dir = Path(args.out) if args.out else None

    metadata = import_design(
        args.niche,
        args.variant,
        args.preview,
        args.canva_design_id,
        pdf_urls=pdf_urls,
        png_urls=png_urls,
        canva_edit_url=args.canva_edit_url,
        out_dir=out_dir,
        price_override=args.price,
    )
    print(f"Imported {metadata['design_id']} -> {metadata['title'][:70]}")


if __name__ == "__main__":
    main()
