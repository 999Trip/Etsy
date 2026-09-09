"""Publish a generated batch as Printify print-on-demand products.

Creates one Printify product per design, using the pod-size PNG as the
print file. Pass --publish to push products live - if the Printify shop
has a connected Etsy store (Printify dashboard > My stores > Connect a
new store store > Etsy), publishing a product automatically creates the
matching Etsy listing, so no separate Etsy write access is needed for
physical products.

Usage:
    python -m pipeline.publish_pod --batch output/boho_line_art_wall_decor \\
        --shop-id 12345 --blueprint-id 494 --print-provider-id 1 \\
        --variant-ids 33742,33743 --publish

Find blueprint/print-provider/variant ids with:
    python -c "from integrations.printify_client import PrintifyClient as P; \\
        import json; print(json.dumps(P().list_blueprints()[:10], indent=2))"
Printify's catalog browser (printify.com/app/products) is usually the
easier way to pick a blueprint (e.g. "Matte Vertical Posters") and see
its blueprint_id / print_provider_id / variant ids in the URL/API calls
the site itself makes.
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
    publish: bool = False,
) -> None:
    client = PrintifyClient()
    metadata_paths = sorted(batch_dir.glob("*/metadata.json"))
    if not metadata_paths:
        print(f"No designs found under {batch_dir} (expected */metadata.json)")
        return

    for meta_path in metadata_paths:
        metadata = json.loads(meta_path.read_text())

        if metadata.get("product_mode") not in ("pod", "both"):
            continue
        if metadata.get("printify_product_id"):
            print(f"skip (already published): {metadata['design_id']}")
            continue

        pod_size = metadata.get("pod_size")
        png_path = metadata.get("files", {}).get("png", {}).get(pod_size)
        if not png_path or not Path(png_path).exists():
            print(f"skip (no print file for size {pod_size}): {metadata['design_id']}")
            continue

        print(f"publishing: {metadata['design_id']} -> {metadata['title'][:60]}")
        image = client.upload_image(png_path)
        product = client.create_product(
            shop_id,
            title=metadata["title"][:255],
            description=metadata["description"],
            blueprint_id=blueprint_id,
            print_provider_id=print_provider_id,
            variant_ids=variant_ids,
            image_id=image["id"],
            price_cents=int(round(metadata["price_pod"] * 100)),
            tags=metadata.get("tags"),
        )
        product_id = product["id"]

        if publish:
            client.publish_product(shop_id, product_id)

        metadata["printify_product_id"] = product_id
        metadata["printify_state"] = "published" if publish else "draft"
        meta_path.write_text(json.dumps(metadata, indent=2))
        print(f"  -> product {product_id} ({'published' if publish else 'draft'})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish a design batch as Printify POD products.")
    parser.add_argument("--batch", required=True, help="Path to a batch output dir (from pipeline.generate)")
    parser.add_argument("--shop-id", default=os.environ.get("PRINTIFY_SHOP_ID"), help="Printify shop id (or set PRINTIFY_SHOP_ID)")
    parser.add_argument("--blueprint-id", required=True, type=int, help="Printify catalog blueprint id (e.g. a poster/mug product type)")
    parser.add_argument("--print-provider-id", required=True, type=int, help="Printify print provider id for that blueprint")
    parser.add_argument("--variant-ids", required=True, help="Comma-separated variant ids to enable, e.g. 33742,33743")
    parser.add_argument("--publish", action="store_true", help="Publish live (pushes to a connected Etsy shop if configured)")
    args = parser.parse_args()

    if not args.shop_id:
        parser.error("--shop-id is required (or set PRINTIFY_SHOP_ID in .env)")

    variant_ids = [int(v) for v in args.variant_ids.split(",")]
    publish_batch(Path(args.batch), args.shop_id, args.blueprint_id, args.print_provider_id, variant_ids, args.publish)


if __name__ == "__main__":
    main()
