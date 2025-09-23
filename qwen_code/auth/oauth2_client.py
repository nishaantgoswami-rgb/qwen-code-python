"""
Qwen OAuth2 implementation for device code flow with automatic token refresh.
This implementation mirrors Qwen.ai's TypeScript implementation.
"""

import base64
import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
import httpx

# OAuth2 endpoints
OAUTH_BASE_URL = "https://chat.qwen.ai"
DEVICE_CODE_ENDPOINT = f"{OAUTH_BASE_URL}/api/v1/oauth2/device/code"
TOKEN_ENDPOINT = f"{OAUTH_BASE_URL}/api/v1/oauth2/token"

CLIENT_ID = "f0304373b74a44d2b584a3fb70ca9e56"
SCOPE = "openid profile email model.completion"
CREDENTIALS_FILE = Path.home() / ".qwen" / "regular_oauth_creds.json"

# Import the DashScope token exchange mechanism
from qwen_code.auth.dashscope_exchange import DashScopeTokenExchange


def _generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE verifier and challenge."""
    verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _save_credentials(creds: Dict[str, Any]) -> None:
    """Save credentials to JSON file."""
    CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(json.dumps(creds))


def _load_credentials() -> Optional[Dict[str, Any]]:
    """Load credentials from JSON file."""
    if CREDENTIALS_FILE.exists():
        return json.loads(CREDENTIALS_FILE.read_text())
    return None


class QwenOAuth2Client:
    """Qwen OAuth2 client with automatic token refresh."""
    
    def __init__(self):
        self._creds = _load_credentials() or {}

    def get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        # Check if we have a valid access token
        if self._creds.get("access_token") and time.time() < self._creds.get("expiry", 0):
            return self._creds["access_token"]
        
        # Attempt refresh if expired
        if self._creds.get("refresh_token"):
            try:
                self._refresh_token()
                return self._creds["access_token"]
            except Exception:
                # If refresh fails, fall through to device flow
                pass
        
        # Otherwise do device flow
        return self._device_flow()

    def get_dashscope_api_key(self) -> str:
        """Get a valid DashScope API key by exchanging the OAuth token."""
        oauth_token = self.get_access_token()
        api_key = DashScopeTokenExchange.exchange_token_sync(oauth_token)
        if not api_key:
            raise Exception("Failed to exchange OAuth token for DashScope API key")
        return api_key

    def _device_flow(self) -> str:
        """Perform device code flow authentication."""
        verifier, challenge = _generate_pkce_pair()
        data = {
            "client_id": CLIENT_ID,
            "scope": SCOPE,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        
        # Add headers for proper content type
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Qwen-Code-CLI/1.0"
        }
        
        r = httpx.post(DEVICE_CODE_ENDPOINT, data=data, headers=headers)
        r.raise_for_status()
        device = r.json()
        
        print("Visit:", device["verification_uri_complete"])
        expiry = time.time() + device["expires_in"]
        interval = device.get("interval", 2)

        while time.time() < expiry:
            time.sleep(interval)
            payload = {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": CLIENT_ID,
                "device_code": device["device_code"],
                "code_verifier": verifier,
            }
            
            # Add headers for proper content type
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Qwen-Code-CLI/1.0"
            }
            
            resp = httpx.post(TOKEN_ENDPOINT, data=payload, headers=headers)
            if resp.status_code == 200:
                token_data = resp.json()
                break
            err = resp.json().get("error")
            if err not in ("authorization_pending", "slow_down"):
                resp.raise_for_status()
            if err == "slow_down":
                interval += 2
        else:
            raise TimeoutError("Device authorization timed out")

        self._store_token_data(token_data)
        return token_data["access_token"]

    def _refresh_token(self) -> None:
        """Refresh the access token using the refresh token."""
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self._creds["refresh_token"],
            "client_id": CLIENT_ID,
        }
        
        # Add headers for proper content type
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Qwen-Code-CLI/1.0"
        }
        
        r = httpx.post(TOKEN_ENDPOINT, data=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        self._store_token_data(data)

    def _store_token_data(self, data: Dict[str, Any]) -> None:
        """Store token data with expiration time."""
        self._creds = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", self._creds.get("refresh_token")),
            "expiry": time.time() + data.get("expires_in", 0),
            # Persist the resource_url returned by Qwen.ai
            "resource_url": data.get("resource_url"),
        }
        _save_credentials(self._creds)
        
        # Clear the DashScope API key cache when OAuth tokens change
        DashScopeTokenExchange.clear_cache()