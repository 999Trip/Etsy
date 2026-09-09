"""One-time OAuth2 (Authorization Code + PKCE) flow for the Etsy API v3.

Etsy requires OAuth for any write operation (creating listings, uploading
files/images), unlike Printify's simple personal access token. Run this
once on the machine where you'll actually use a browser:

    python -m integrations.etsy_oauth

It will:
  1. Print an authorization URL - open it in your browser and approve access.
  2. Etsy redirects to a local server this script starts (http://localhost:3003/oauth/redirect).
  3. The script exchanges the returned code for an access + refresh token
     and saves them to .etsy_token.json (gitignored) in the repo root.

Requires ETSY_KEYSTRING (your app's "Keystring"/client ID) to be set in
.env - register an app at https://www.etsy.com/developers/register first.

integrations/etsy_client.py reads .etsy_token.json and refreshes the
access token automatically using the stored refresh token, so this only
needs to be run again if the refresh token itself expires or is revoked.
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import secrets
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN_PATH = Path(__file__).resolve().parent.parent / ".etsy_token.json"
AUTH_URL = "https://www.etsy.com/oauth/connect"
TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
REDIRECT_PORT = 3003
REDIRECT_URI = os.environ.get("ETSY_REDIRECT_URI", f"http://localhost:{REDIRECT_PORT}/oauth/redirect")

# Scopes needed to create/manage listings (both digital and physical) and
# read shop info. See https://developers.etsy.com/documentation/essentials/authentication#scopes
DEFAULT_SCOPES = ["listings_r", "listings_w", "listings_d", "shops_r", "transactions_r"]


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    result: dict = {}

    def do_GET(self):  # noqa: N802 (http.server API)
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        _CallbackHandler.result["code"] = params.get("code", [None])[0]
        _CallbackHandler.result["state"] = params.get("state", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body>Authorized - you can close this tab.</body></html>")

    def log_message(self, *args):  # silence default logging
        pass


def run_oauth_flow(scopes: list[str] | None = None) -> dict:
    keystring = os.environ.get("ETSY_KEYSTRING")
    if not keystring:
        raise RuntimeError("Set ETSY_KEYSTRING in .env before running the OAuth flow.")

    scopes = scopes or DEFAULT_SCOPES
    state = secrets.token_urlsafe(16)
    code_verifier = _b64url(secrets.token_bytes(40))
    code_challenge = _b64url(hashlib.sha256(code_verifier.encode("ascii")).digest())

    query = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": keystring,
            "redirect_uri": REDIRECT_URI,
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    auth_url = f"{AUTH_URL}?{query}"

    server = http.server.HTTPServer(("localhost", REDIRECT_PORT), _CallbackHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    print("Open this URL in your browser and approve access:\n")
    print(auth_url)
    print(f"\nWaiting for the redirect on {REDIRECT_URI} ...")
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    thread.join(timeout=300)
    result = _CallbackHandler.result
    if not result.get("code"):
        raise RuntimeError("Timed out waiting for the Etsy OAuth redirect.")
    if result.get("state") != state:
        raise RuntimeError("OAuth state mismatch - possible CSRF, aborting.")

    resp = requests.post(
        TOKEN_URL,
        json={
            "grant_type": "authorization_code",
            "client_id": keystring,
            "redirect_uri": REDIRECT_URI,
            "code": result["code"],
            "code_verifier": code_verifier,
        },
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json()
    token["obtained_at"] = time.time()
    TOKEN_PATH.write_text(json.dumps(token, indent=2))
    print(f"\nSaved token to {TOKEN_PATH}")
    return token


if __name__ == "__main__":
    run_oauth_flow()
