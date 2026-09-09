"""Minimal Printify REST API (v1) client.

Docs: https://developers.printify.com/

Auth is a single personal access token from
https://printify.com/app/account/api - no OAuth flow needed. Printify can
publish products directly to a connected Etsy shop (Printify > My stores
> connect Etsy), which is how the POD pipeline in this repo reaches Etsy
without needing Etsy write-scoped credentials for physical products.
"""
from __future__ import annotations

import base64
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://api.printify.com/v1"


class PrintifyError(RuntimeError):
    pass


class PrintifyClient:
    def __init__(self, api_token: str | None = None, timeout: int = 60):
        self.api_token = api_token or os.environ.get("PRINTIFY_API_TOKEN")
        if not self.api_token:
            raise PrintifyError(
                "No Printify API token. Set PRINTIFY_API_TOKEN in .env "
                "(from https://printify.com/app/account/api)."
            )
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "User-Agent": "etsy-printify-automation/1.0",
            }
        )

    def _request(self, method: str, path: str, retries: int = 3, **kwargs) -> Any:
        url = f"{API_BASE}{path}"
        last_exc: Exception | None = None
        for attempt in range(retries):
            resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
            if resp.status_code == 429:
                # Rate limited - Printify sends Retry-After.
                wait = int(resp.headers.get("Retry-After", 2 ** attempt))
                time.sleep(wait)
                continue
            if not resp.ok:
                raise PrintifyError(f"{method} {path} -> {resp.status_code}: {resp.text}")
            return resp.json() if resp.content else None
        raise PrintifyError(f"{method} {path} failed after {retries} retries") from last_exc

    # ---- shops -----------------------------------------------------
    def list_shops(self) -> list[dict]:
        return self._request("GET", "/shops.json")

    # ---- catalog -----------------------------------------------------
    def list_blueprints(self) -> list[dict]:
        return self._request("GET", "/catalog/blueprints.json")

    def get_blueprint(self, blueprint_id: int) -> dict:
        return self._request("GET", f"/catalog/blueprints/{blueprint_id}.json")

    def list_print_providers(self, blueprint_id: int) -> list[dict]:
        return self._request("GET", f"/catalog/blueprints/{blueprint_id}/print_providers.json")

    def list_variants(self, blueprint_id: int, print_provider_id: int) -> dict:
        return self._request(
            "GET",
            f"/catalog/blueprints/{blueprint_id}/print_providers/{print_provider_id}/variants.json",
        )

    # ---- images -----------------------------------------------------
    def upload_image(self, file_path: str | Path) -> dict:
        """Upload a local image; Printify returns an image id used in print areas."""
        file_path = Path(file_path)
        contents = base64.b64encode(file_path.read_bytes()).decode("ascii")
        body = {"file_name": file_path.name, "contents": contents}
        return self._request("POST", "/uploads/images.json", json=body)

    # ---- products -----------------------------------------------------
    def create_product(
        self,
        shop_id: str,
        *,
        title: str,
        description: str,
        blueprint_id: int,
        print_provider_id: int,
        variant_ids: list[int],
        image_id: str,
        price_cents: int,
        tags: list[str] | None = None,
        placement: str = "front",
        scale: float = 1.0,
        x: float = 0.5,
        y: float = 0.5,
        angle: float = 0.0,
    ) -> dict:
        body = {
            "title": title,
            "description": description,
            "blueprint_id": blueprint_id,
            "print_provider_id": print_provider_id,
            "variants": [
                {"id": vid, "price": price_cents, "is_enabled": True} for vid in variant_ids
            ],
            "print_areas": [
                {
                    "variant_ids": variant_ids,
                    "placeholders": [
                        {
                            "position": placement,
                            "images": [
                                {
                                    "id": image_id,
                                    "x": x,
                                    "y": y,
                                    "scale": scale,
                                    "angle": angle,
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        if tags:
            body["tags"] = tags
        return self._request("POST", f"/shops/{shop_id}/products.json", json=body)

    def publish_product(self, shop_id: str, product_id: str) -> None:
        """Publish a product - if the shop's Etsy integration is connected,
        this creates/updates the live Etsy listing automatically."""
        body = {
            "title": True,
            "description": True,
            "images": True,
            "variants": True,
            "tags": True,
            "keyFeatures": True,
            "shipping_template": True,
        }
        self._request("POST", f"/shops/{shop_id}/products/{product_id}/publish.json", json=body)

    def get_product(self, shop_id: str, product_id: str) -> dict:
        return self._request("GET", f"/shops/{shop_id}/products/{product_id}.json")
