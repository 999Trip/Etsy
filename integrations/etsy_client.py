"""Minimal Etsy Open API v3 client.

Docs: https://developers.etsy.com/documentation/reference

Auth is OAuth2 (Authorization Code + PKCE) - see etsy_oauth.py for the
one-time browser flow that produces .etsy_token.json. This client loads
that file and refreshes the access token automatically using the stored
refresh token.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://api.etsy.com/v3/application"
TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
TOKEN_PATH = Path(__file__).resolve().parent.parent / ".etsy_token.json"


class EtsyError(RuntimeError):
    pass


class EtsyClient:
    def __init__(
        self,
        keystring: str | None = None,
        shared_secret: str | None = None,
        token_path: Path = TOKEN_PATH,
        timeout: int = 60,
    ):
        self.keystring = keystring or os.environ.get("ETSY_KEYSTRING")
        if not self.keystring:
            raise EtsyError("Set ETSY_KEYSTRING in .env (from your Etsy developer app).")
        self.shared_secret = shared_secret or os.environ.get("ETSY_SHARED_SECRET")
        if not self.shared_secret:
            raise EtsyError("Set ETSY_SHARED_SECRET in .env (the 'Shared secret' on your Etsy app's page).")
        self.token_path = token_path
        self.timeout = timeout
        self._token = self._load_token()
        self.session = requests.Session()

    # ---- token handling -----------------------------------------------------
    def _load_token(self) -> dict:
        if not self.token_path.exists():
            raise EtsyError(
                "No Etsy token found. Run `python -m integrations.etsy_oauth` once to "
                "authorize this app in a browser."
            )
        return json.loads(self.token_path.read_text())

    def _save_token(self, token: dict) -> None:
        token["obtained_at"] = time.time()
        self.token_path.write_text(json.dumps(token, indent=2))
        self._token = token

    def _refresh_if_needed(self) -> None:
        obtained_at = self._token.get("obtained_at", 0)
        expires_in = self._token.get("expires_in", 3600)
        if time.time() <= obtained_at + expires_in - 60:
            return
        resp = requests.post(
            TOKEN_URL,
            json={
                "grant_type": "refresh_token",
                "client_id": self.keystring,
                "refresh_token": self._token["refresh_token"],
            },
            timeout=self.timeout,
        )
        if not resp.ok:
            raise EtsyError(f"Failed to refresh Etsy token: {resp.status_code} {resp.text}")
        self._save_token(resp.json())

    def _headers(self) -> dict:
        self._refresh_if_needed()
        return {
            "Authorization": f"Bearer {self._token['access_token']}",
            "x-api-key": f"{self.keystring}:{self.shared_secret}",
        }

    def _request(self, method: str, path: str, files=None, **kwargs) -> Any:
        url = f"{API_BASE}{path}"
        resp = self.session.request(method, url, headers=self._headers(), files=files, timeout=self.timeout, **kwargs)
        if not resp.ok:
            raise EtsyError(f"{method} {path} -> {resp.status_code}: {resp.text}")
        return resp.json() if resp.content else None

    # ---- shops -----------------------------------------------------
    def get_shop(self, shop_id: str) -> dict:
        return self._request("GET", f"/shops/{shop_id}")

    # ---- taxonomy (needed once per niche to find a category id) -------------
    def get_seller_taxonomy_nodes(self) -> list[dict]:
        return self._request("GET", "/seller-taxonomy/nodes")["results"]

    # ---- listings -----------------------------------------------------
    def create_draft_listing(
        self,
        shop_id: str,
        *,
        title: str,
        description: str,
        price: float,
        quantity: int,
        taxonomy_id: int,
        tags: list[str] | None = None,
        who_made: str = "i_did",
        when_made: str = "made_to_order",
        listing_type: str = "download",
        shipping_profile_id: int | None = None,
        materials: list[str] | None = None,
        is_supply: bool = False,
    ) -> dict:
        """Create a draft listing. listing_type: 'download' (digital),
        'physical', or 'both'. shipping_profile_id is required unless
        listing_type == 'download'."""
        if listing_type != "download" and not shipping_profile_id:
            raise EtsyError("shipping_profile_id is required for physical/both listings.")

        body: dict[str, Any] = {
            "quantity": quantity,
            "title": title[:140],
            "description": description,
            "price": round(price, 2),
            "who_made": who_made,
            "when_made": when_made,
            "taxonomy_id": taxonomy_id,
            "type": listing_type,
            "is_supply": is_supply,
        }
        if tags:
            body["tags"] = tags[:13]
        if materials:
            body["materials"] = materials
        if shipping_profile_id:
            body["shipping_profile_id"] = shipping_profile_id

        return self._request("POST", f"/shops/{shop_id}/listings", json=body)

    def upload_listing_image(self, shop_id: str, listing_id: int, image_path: str | Path, rank: int = 1) -> dict:
        image_path = Path(image_path)
        with open(image_path, "rb") as fh:
            files = {"image": (image_path.name, fh, "image/jpeg")}
            return self._request(
                "POST",
                f"/shops/{shop_id}/listings/{listing_id}/images",
                files=files,
                data={"rank": rank},
            )

    def upload_listing_file(
        self, shop_id: str, listing_id: int, file_path: str | Path, name: str | None = None, rank: int = 1
    ) -> dict:
        """Attach a digital file (e.g. the print-ready PDF) to a digital listing."""
        file_path = Path(file_path)
        with open(file_path, "rb") as fh:
            files = {"file": (file_path.name, fh, "application/octet-stream")}
            return self._request(
                "POST",
                f"/shops/{shop_id}/listings/{listing_id}/files",
                files=files,
                data={"name": name or file_path.stem, "rank": rank},
            )

    def update_listing(self, shop_id: str, listing_id: int, **fields: Any) -> dict:
        return self._request("PATCH", f"/shops/{shop_id}/listings/{listing_id}", json=fields)

    def activate_listing(self, shop_id: str, listing_id: int) -> dict:
        """Move a listing from draft to active (publicly visible on Etsy).
        Etsy requires at least one image before a listing can go active."""
        return self.update_listing(shop_id, listing_id, state="active")

    def delete_listing(self, listing_id: int) -> None:
        self._request("DELETE", f"/listings/{listing_id}")
