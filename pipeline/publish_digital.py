"""Publish a generated batch as Etsy digital-download listings.

Creates one Etsy listing per design (as a DRAFT by default - pass
--activate to make listings live immediately), uploads the preview image
and the print-ready PDF(s), and writes the resulting listing id back into
each design's metadata.json so re-running the script is idempotent.

Usage:
    python -m pipeline.publish_digital --batch output/minimalist_quote_posters \\
        --taxonomy-id 1234 --shop-id 56789012

Find your taxonomy_id with:
    python -c "from integrations.etsy_client import EtsyClient; \\
        [print(n['id'], n['name']) for n in EtsyClient().get_seller_taxonomy_nodes()]"
(Digital wall art / printables commonly live under "Craft Supplies & Tools >
Digital > Patterns & How To" or "Art & Collectibles > Prints" - browse the
nodes and pick whichever matches your niche.)
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from integrations.etsy_client import EtsyClient

load_dotenv()


def _load_designs(batch_dir: Path) -> list[Path]:
    return sorted(p for p in batch_dir.glob("*/metadata.json"))


def publish_batch(
    batch_dir: Path,
    shop_id: str,
    taxonomy_id: int,
    quantity: int = 999,
    activate: bool = False,
) -> None:
    client = EtsyClient()
    metadata_paths = _load_designs(batch_dir)
    if not metadata_paths:
        print(f"No designs found under {batch_dir} (expected */metadata.json)")
        return

    for meta_path in metadata_paths:
        metadata = json.loads(meta_path.read_text())

        if metadata.get("product_mode") not in ("digital", "both"):
            continue
        if metadata.get("etsy_listing_id"):
            print(f"skip (already published): {metadata['design_id']}")
            continue

        print(f"publishing: {metadata['design_id']} -> {metadata['title'][:60]}")
        listing = client.create_draft_listing(
            shop_id,
            title=metadata["title"],
            description=metadata["description"],
            price=metadata["price_digital"],
            quantity=quantity,
            taxonomy_id=taxonomy_id,
            tags=metadata["tags"],
            listing_type="download",
        )
        listing_id = listing["listing_id"]

        preview = metadata.get("preview")
        if preview and Path(preview).exists():
            client.upload_listing_image(shop_id, listing_id, preview, rank=1)

        # Prefer PDF as the deliverable file; fall back to PNG for designs
        # that only have one (e.g. Canva exports whose native aspect ratio
        # doesn't map to a standard PDF paper size - see canva_import.py).
        deliverable_files = metadata.get("files", {}).get("pdf") or metadata.get("files", {}).get("png", {})
        for rank, (size_name, file_path) in enumerate(deliverable_files.items(), start=1):
            client.upload_listing_file(shop_id, listing_id, file_path, name=f"{metadata['design_id']}_{size_name}", rank=rank)

        if activate:
            client.activate_listing(shop_id, listing_id)

        metadata["etsy_listing_id"] = listing_id
        metadata["etsy_state"] = "active" if activate else "draft"
        meta_path.write_text(json.dumps(metadata, indent=2))
        print(f"  -> listing {listing_id} ({'active' if activate else 'draft'})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish a design batch as Etsy digital listings.")
    parser.add_argument("--batch", required=True, help="Path to a batch output dir (from pipeline.generate)")
    parser.add_argument("--shop-id", default=os.environ.get("ETSY_SHOP_ID"), help="Etsy shop id (or set ETSY_SHOP_ID)")
    parser.add_argument("--taxonomy-id", required=True, type=int, help="Etsy seller-taxonomy category id")
    parser.add_argument("--quantity", type=int, default=999, help="Listing quantity (digital downloads never deplete)")
    parser.add_argument("--activate", action="store_true", help="Publish live instead of leaving as a draft")
    args = parser.parse_args()

    if not args.shop_id:
        parser.error("--shop-id is required (or set ETSY_SHOP_ID in .env)")

    publish_batch(Path(args.batch), args.shop_id, args.taxonomy_id, args.quantity, args.activate)


if __name__ == "__main__":
    main()
