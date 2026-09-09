"""Batch design generator.

Reads a niche definition from config/niches.yaml and renders a batch of
finished designs (print-ready PNG/PDF + a web preview JPG per size) plus
an Etsy/Printify-ready metadata.json for each design.

Usage:
    python -m pipeline.generate --niche boho_line_art_wall_decor --count 6 \\
        --out output/batch_001
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import re
import textwrap
from pathlib import Path

import yaml

from design.generators import GENERATORS

NICHES_PATH = Path(__file__).resolve().parent.parent / "config" / "niches.yaml"

# Etsy hard limits (API v3): titles <= 140 chars, at most 13 tags of
# <= 20 chars each.
ETSY_MAX_TITLE = 140
ETSY_MAX_TAGS = 13
ETSY_MAX_TAG_LEN = 20


def humanize(slug: str) -> str:
    return slug.replace("_", " ").replace("-", " ").title()


def load_niches(path: Path = NICHES_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["niches"]


def _slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text[:60] or "design"


def _render_seo(niche: dict, context: dict) -> dict:
    title = re.sub(r"\s+", " ", niche["seo"]["title_template"].format(**context)).strip()
    if len(title) > ETSY_MAX_TITLE:
        title = title[:ETSY_MAX_TITLE].rsplit(" ", 1)[0]
    description = niche["seo"]["description_template"].format(**context).strip()
    tags = [t for t in niche["seo"]["tags"] if len(t) <= ETSY_MAX_TAG_LEN][:ETSY_MAX_TAGS]
    return {"title": title, "description": description, "tags": tags}


def _iter_variants(niche: dict, count: int, rng: random.Random) -> list[tuple[str, object]]:
    """Return `count` (palette, extra) combinations, covering every
    combination once before repeating any."""
    palettes = list(niche["palettes"])
    rng.shuffle(palettes)

    extras = list(niche["quotes"] if niche["type"] == "quote_poster" else niche["motifs"])
    rng.shuffle(extras)

    combos = list(itertools.product(palettes, extras))
    rng.shuffle(combos)
    if count > len(combos):
        combos = combos * (count // len(combos) + 1)
    return combos[:count]


def generate_batch(niche_name: str, count: int, out_dir: Path, seed: int | None = None) -> list[dict]:
    niches = load_niches()
    if niche_name not in niches:
        raise KeyError(f"Unknown niche '{niche_name}'. Available: {', '.join(sorted(niches))}")
    niche = niches[niche_name]
    rng = random.Random(seed)
    generator = GENERATORS[niche["type"]]

    digital_sizes = niche.get("digital_sizes", [])
    pod_size = niche.get("pod_size")
    product_mode = niche.get("product_mode", "digital")
    all_sizes = list(dict.fromkeys(digital_sizes + ([pod_size] if pod_size else [])))
    preview_size = pod_size or (digital_sizes[0] if digital_sizes else all_sizes[0])

    out_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for i, (palette_name, extra) in enumerate(_iter_variants(niche, count, rng)):
        design_seed = rng.randint(0, 2**31 - 1)

        if niche["type"] == "quote_poster":
            quote_text, author = extra["text"], extra.get("author")
            gen_kwargs = {"quote": quote_text, "author": author}
            context = {
                "quote": quote_text,
                "quote_short": textwrap.shorten(quote_text, width=40, placeholder="..."),
                "palette_title": humanize(palette_name),
                "motif_title": "",
            }
            design_slug = _slugify(f"{niche_name}-{quote_text}-{palette_name}-{i}")
        else:
            motif = extra
            gen_kwargs = {"motif": motif}
            context = {
                "motif_title": humanize(motif),
                "palette_title": humanize(palette_name),
                "quote": "",
                "quote_short": "",
            }
            design_slug = _slugify(f"{niche_name}-{motif}-{palette_name}-{i}")

        design_dir = out_dir / design_slug
        files: dict[str, dict[str, str]] = {}
        preview_path = design_dir / "preview.jpg"

        for size_name in all_sizes:
            canvas = generator(palette_name=palette_name, size_name=size_name, seed=design_seed, **gen_kwargs)
            png_path = design_dir / f"{size_name}.png"
            canvas.save_png(png_path)
            files.setdefault("png", {})[size_name] = str(png_path)

            if size_name in digital_sizes:
                pdf_path = design_dir / f"{size_name}.pdf"
                canvas.save_pdf(pdf_path)
                files.setdefault("pdf", {})[size_name] = str(pdf_path)

            if size_name == preview_size:
                canvas.save_preview_jpg(preview_path)

        seo = _render_seo(niche, context)

        metadata = {
            "design_id": design_slug,
            "niche": niche_name,
            "product_mode": product_mode,
            "palette": palette_name,
            "generator_type": niche["type"],
            "generator_kwargs": gen_kwargs,
            "seed": design_seed,
            "title": seo["title"],
            "description": seo["description"],
            "tags": seo["tags"],
            "price_digital": niche.get("price_digital"),
            "price_pod": niche.get("price_pod"),
            "pod_size": pod_size,
            "digital_sizes": digital_sizes,
            "preview": str(preview_path),
            "files": files,
        }
        with open(design_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        results.append(metadata)

    with open(out_dir / "batch.json", "w", encoding="utf-8") as f:
        json.dump(
            {"niche": niche_name, "count": len(results), "designs": [m["design_id"] for m in results]},
            f,
            indent=2,
        )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a batch of designs for a niche.")
    parser.add_argument("--niche", required=True, help="Niche name from config/niches.yaml")
    parser.add_argument("--count", type=int, default=5, help="Number of designs to generate")
    parser.add_argument("--out", default=None, help="Output directory (default: output/<niche>)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for a reproducible batch")
    args = parser.parse_args()

    out_dir = Path(args.out) if args.out else Path("output") / args.niche
    results = generate_batch(args.niche, args.count, out_dir, seed=args.seed)

    print(f"Generated {len(results)} designs into {out_dir}/")
    for m in results:
        print(f"  - {m['design_id']}  ({m['title'][:70]})")


if __name__ == "__main__":
    main()
