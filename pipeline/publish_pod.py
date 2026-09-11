"""Publish a generated batch as Printify print-on-demand products.

Creates one Printify product per design, using a print file matching
--print-size as the artwork. Pass --publish to push products live - if
the Printify shop has a connected Etsy store (Printify dashboard > My
stores > Connect a new store > Etsy), publishing a product automatically
creates the matching Etsy listing, so no separate Etsy write access is
needed for physical products.

A single batch of designs can be published to *multiple* product types
(e.g. a t-shirt and a mug) by running this script once per blueprint -
each run is tracked separately in metadata.json (keyed by blueprint id),
so re-running with a different --blueprint-id adds a new product instead
of being skipped as already-published.

Usage:
    # T-shirts (portrait print area)
    python -m pipeline.publish_pod --batch output/halloween_apparel_graphics \\
        --shop-id 12345 --blueprint-id 6 --print-provider-id 1 \\
        --variant-ids 12100,12101 --print-size apparel_12x16 --publish

    # The same batch, also as mugs (landscape wrap print area)
    python -m pipeline.publish_pod --batch output/halloween_apparel_graphics \\
        --shop-id 12345 --blueprint-id 68 --print-provider-id 27 \\
        --variant-ids 33843 --print-size mug_9x4 --price 14.99 --publish

Find blueprint/print-provider/variant ids with:
    python -c "from integrations.printify_client import PrintifyClient as P; \\
        import json; print(json.dumps(P().list_blueprints()[:10], indent=2))"
Printify's catalog browser (printify.com/app/products) is usually the
easier way to pick a blueprint (e.g. "Unisex Heavy Cotton Tee" or "11oz
Mug") and see its blueprint_id / print_provider_id / variant ids in the
URL/API calls the site itself makes.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from integrations.printify_client import PrintifyClient

load_dotenv()


def publish_batch(
    batch_dir: Path,
    shop_id: str,
    blueprint_id: int,
    print_provider_id: int,
    variant_ids: list[int],
    print_size: str | None = None,
    price: float | None = None,
    publish: bool = False,
) -> None:
    client = PrintifyClient()
    metadata_paths = sorted(batch_dir.glob("*/metadata.json"))
    if not metadata_paths:
        print(f"No designs found under {batch_dir} (expected */metadata.json)")
        return

    blueprint_key = str(blueprint_id)

    for meta_path in metadata_paths:
        metadata = json.loads(meta_path.read_text())

        if metadata.get("product_mode") not in ("pod", "both"):
            continue
        existing_products = metadata.setdefault("printify_products", {})
        if blueprint_key in existing_products:
            print(f"skip (already published to blueprint {blueprint_id}): {metadata['design_id']}")
            continue

        size = print_size or (metadata.get("pod_sizes") or [None])[0]
        png_path = metadata.get("files", {}).get("png", {}).get(size)
        if not png_path or not Path(png_path).exists():
            print(f"skip (no print file for size {size}): {metadata['design_id']}")
            continue

        listing_price = price if price is not None else metadata["price_pod"]

        print(f"publishing: {metadata['design_id']} -> {metadata['title'][:60]} ({size})")
        image = client.upload_image(png_path)
        product = client.create_product(
            shop_id,
            title=metadata["title"][:255],
            description=metadata["description"],
            blueprint_id=blueprint_id,
            print_provider_id=print_provider_id,
            variant_ids=variant_ids,
            image_id=image["id"],
            price_cents=int(round(listing_price * 100)),
            tags=metadata.get("tags"),
        )
        product_id = product["id"]

        if publish:
            client.publish_product(shop_id, product_id)

        existing_products[blueprint_key] = {
            "product_id": product_id,
            "print_size": size,
            "state": "published" if publish else "draft",
        }
        meta_path.write_text(json.dumps(metadata, indent=2))
        print(f"  -> product {product_id} ({'published' if publish else 'draft'})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish a design batch as Printify POD products.")
    parser.add_argument("--batch", required=True, help="Path to a batch output dir (from pipeline.generate)")
    parser.add_argument("--shop-id", default=os.environ.get("PRINTIFY_SHOP_ID"), help="Printify shop id (or set PRINTIFY_SHOP_ID)")
    parser.add_argument("--blueprint-id", required=True, type=int, help="Printify catalog blueprint id (a specific product type, e.g. a tee or mug)")
    parser.add_argument("--print-provider-id", required=True, type=int, help="Printify print provider id for that blueprint")
    parser.add_argument("--variant-ids", required=True, help="Comma-separated variant ids to enable, e.g. 33742,33743")
    parser.add_argument("--print-size", default=None, help="Which generated size to use as the print file (e.g. apparel_12x16, mug_9x4). Defaults to the niche's first pod size.")
    parser.add_argument("--price", type=float, default=None, help="Override the niche's default price_pod for this product type (e.g. a lower price for mugs than shirts)")
    parser.add_argument("--publish", action="store_true", help="Publish live (pushes to a connected Etsy shop if configured)")
    args = parser.parse_args()

    if not args.shop_id:
        parser.error("--shop-id is required (or set PRINTIFY_SHOP_ID in .env)")

    variant_ids = [int(v) for v in args.variant_ids.split(",")]
    publish_batch(
        Path(args.batch),
        args.shop_id,
        args.blueprint_id,
        args.print_provider_id,
        variant_ids,
        print_size=args.print_size,
        price=args.price,
        publish=args.publish,
    )


if __name__ == "__main__":
    main()
