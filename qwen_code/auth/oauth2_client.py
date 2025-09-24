"""
Qwen OAuth2 implementation for authorization code flow with PKCE and automatic token refresh.
This implementation follows the OAuth2 specification as detailed in the API documentation.
"""

import base64
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any
import httpx

# OAuth2 endpoints as specified in the API documentation
OAUTH_BASE_URL = "https://chat.qwen.ai"
TOKEN_ENDPOINT = f"{OAUTH_BASE_URL}/api/v1/oauth2/token"
DEVICE_CODE_ENDPOINT = f"{OAUTH_BASE_URL}/api/v1/oauth2/device/code"

# Client configuration - these values should come from environment/config
DEFAULT_CLIENT_ID = os.getenv("QWEN_CLIENT_ID", "f0304373b74a44d2b584a3fb70ca9e56")
DEFAULT_REDIRECT_URI = os.getenv("QWEN_REDIRECT_URI", "http://localhost:8080/callback")
DEFAULT_SCOPE = "openid profile email model.completion"

CREDENTIALS_FILE = Path.home() / ".qwen" / "oauth_creds.json"

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
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(creds, f)


def _load_credentials() -> Optional[Dict[str, Any]]:
    """Load credentials from JSON file."""
    if CREDENTIALS_FILE.exists():
        try:
            with open(CREDENTIALS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


class QwenOAuth2Client:
    """Qwen OAuth2 client with automatic token refresh."""
    
    def __init__(self, client_id: Optional[str] = None, redirect_uri: Optional[str] = None):
        self.client_id = client_id or DEFAULT_CLIENT_ID
        self.redirect_uri = redirect_uri or DEFAULT_REDIRECT_URI
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
            "client_id": self.client_id,
            "scope": DEFAULT_SCOPE,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        
        # Add headers for proper content type
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Qwen-Code-CLI/1.0"
        }
        
        with httpx.Client() as client:
            response = client.post(DEVICE_CODE_ENDPOINT, data=data, headers=headers)
            response.raise_for_status()
            device = response.json()
            
            auth_url = device['verification_uri_complete']
            print(f"Visit: {auth_url}")
            
            # Attempt to open the browser automatically
            try:
                import webbrowser
                webbrowser.open(auth_url)
            except Exception as e:
                print(f"Could not automatically open browser: {e}")
                print("Please manually open the URL in your browser.")
            expiry = time.time() + device["expires_in"]
            interval = device.get("interval", 5)

            while time.time() < expiry:
                time.sleep(interval)
                payload = {
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "client_id": self.client_id,
                    "device_code": device["device_code"],
                    "code_verifier": verifier,
                }
                
                # Add headers for proper content type
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "Qwen-Code-CLI/1.0"
                }
                
                resp = client.post(TOKEN_ENDPOINT, data=payload, headers=headers)
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
            "client_id": self.client_id,
        }
        
        # Add headers for proper content type
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Qwen-Code-CLI/1.0"
        }
        
        with httpx.Client() as client:
            response = client.post(TOKEN_ENDPOINT, data=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            self._store_token_data(data)

    def _store_token_data(self, data: Dict[str, Any]) -> None:
        """Store token data with expiration time."""
        self._creds = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", self._creds.get("refresh_token")),
            "expiry": time.time() + data.get("expires_in", 0),
            # Persist the resource_url if returned by Qwen.ai
            "resource_url": data.get("resource_url"),
        }
        _save_credentials(self._creds)
        
        # Clear the DashScope API key cache when OAuth tokens change
        DashScopeTokenExchange.clear_cache()