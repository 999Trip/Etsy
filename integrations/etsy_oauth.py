"""One-time OAuth2 (Authorization Code + PKCE) flow for the Etsy API v3.

Etsy requires OAuth for any write operation (creating listings, uploading
files/images), unlike Printify's simple personal access token. Run this
once on the machine where you'll actually use a browser:

    python -m integrations.etsy_oauth

It will:
  1. Print an authorization URL - open it in your browser and approve access.
  2. Etsy redirects to a local server this script starts
     (https://localhost:3003/oauth/redirect - see note below on why this
     has to be https, even for localhost).
  3. The script exchanges the returned code for an access + refresh token
     and saves them to .etsy_token.json (gitignored) in the repo root.

Requires ETSY_KEYSTRING (your app's "Keystring"/client ID) to be set in
.env - register an app at https://www.etsy.com/developers/register first,
then add this exact redirect URI to it at
https://www.etsy.com/developers/your-apps (character-for-character,
including the "https"; Etsy's docs are explicit that plain http fails,
with no exception for localhost - https://developers.etsy.com/documentation/essentials/authentication/):

    https://localhost:3003/oauth/redirect

Since there's no real HTTPS cert for "localhost", this script generates
a throwaway self-signed one (via `openssl`, cached in the repo root as
.etsy_oauth_cert.pem/.etsy_oauth_key.pem, gitignored) to terminate TLS
for that one local redirect. Your browser will show a privacy/security
warning when it lands on that page after you approve access - that's
expected for a self-signed cert; click through it (e.g. "Advanced" ->
"Proceed to localhost"). The certificate is used only to receive this
one redirect on your own machine; it isn't sent anywhere.

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
import ssl
import subprocess
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN_PATH = Path(__file__).resolve().parent.parent / ".etsy_token.json"
CERT_PATH = Path(__file__).resolve().parent.parent / ".etsy_oauth_cert.pem"
KEY_PATH = Path(__file__).resolve().parent.parent / ".etsy_oauth_key.pem"
AUTH_URL = "https://www.etsy.com/oauth/connect"
TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
REDIRECT_PORT = 3003
REDIRECT_URI = os.environ.get("ETSY_REDIRECT_URI", f"https://localhost:{REDIRECT_PORT}/oauth/redirect")

# Scopes needed to create/manage listings (both digital and physical) and
# read shop info. See https://developers.etsy.com/documentation/essentials/authentication#scopes
DEFAULT_SCOPES = ["listings_r", "listings_w", "listings_d", "shops_r", "transactions_r"]


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _ensure_self_signed_cert() -> None:
    """Generate a throwaway self-signed TLS cert for localhost if one
    isn't already cached, via the system `openssl` CLI (no extra Python
    dependency for something used exactly once per machine)."""
    if CERT_PATH.exists() and KEY_PATH.exists():
        return
    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(KEY_PATH), "-out", str(CERT_PATH),
            "-days", "3650", "-subj", "/CN=localhost",
        ],
        check=True,
        capture_output=True,
    )


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

    _ensure_self_signed_cert()
    server = http.server.HTTPServer(("localhost", REDIRECT_PORT), _CallbackHandler)
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=str(CERT_PATH), keyfile=str(KEY_PATH))
    server.socket = ssl_context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    print("Open this URL in your browser and approve access:\n")
    print(auth_url)
    print(f"\nWaiting for the redirect on {REDIRECT_URI} ...")
    print(
        "(Your browser will show a privacy/security warning when it lands back on "
        "localhost - that's expected, it's a self-signed cert used only for this one "
        "local redirect. Click through it, e.g. 'Advanced' -> 'Proceed to localhost'.)"
    )
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


PENDING_PATH = Path(__file__).resolve().parent.parent / ".etsy_oauth_pending.json"


def start_oauth(scopes: list[str] | None = None) -> str:
    """Manual-handoff variant of run_oauth_flow, for when the browser that
    approves access (e.g. a phone) isn't on the same machine/network as
    this process, so it can't reach a locally-served redirect. Generates
    the PKCE verifier/state and saves them to PENDING_PATH, then returns
    the authorization URL to open manually. Etsy will redirect the
    browser to REDIRECT_URI with ?code=...&state=... - that page won't
    actually load (nothing is listening there), but the code is right
    there in the browser's address bar to copy out. Pass that URL (or
    just the code) to finish_oauth() to complete the exchange."""
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
    PENDING_PATH.write_text(json.dumps({"state": state, "code_verifier": code_verifier}, indent=2))
    return auth_url


def finish_oauth(redirect_url_or_code: str) -> dict:
    """Complete start_oauth() given either the full (unreachable) redirect
    URL the browser landed on, or just the raw `code` value copied from
    it."""
    if not PENDING_PATH.exists():
        raise RuntimeError("No pending OAuth request - call start_oauth() first.")
    pending = json.loads(PENDING_PATH.read_text())

    if redirect_url_or_code.startswith("http"):
        parsed = urllib.parse.urlparse(redirect_url_or_code)
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]
        if not code:
            raise RuntimeError("No 'code' parameter found in that URL.")
        if state != pending["state"]:
            raise RuntimeError("OAuth state mismatch - possible CSRF, aborting.")
    else:
        code = redirect_url_or_code.strip()

    keystring = os.environ.get("ETSY_KEYSTRING")
    resp = requests.post(
        TOKEN_URL,
        json={
            "grant_type": "authorization_code",
            "client_id": keystring,
            "redirect_uri": REDIRECT_URI,
            "code": code,
            "code_verifier": pending["code_verifier"],
        },
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json()
    token["obtained_at"] = time.time()
    TOKEN_PATH.write_text(json.dumps(token, indent=2))
    PENDING_PATH.unlink(missing_ok=True)
    return token


if __name__ == "__main__":
    run_oauth_flow()
