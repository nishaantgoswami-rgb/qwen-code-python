"""
Enhanced Qwen OAuth2 implementation with DashScope API key exchange.
This implementation handles device-code OAuth2 authentication, automatic token refresh,
and exchanges OAuth tokens for DashScope API keys.
"""

import base64
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any
import httpx

# OAuth2 endpoints
OAUTH_BASE_URL = "https://chat.qwen.ai"
DEVICE_CODE_ENDPOINT = f"{OAUTH_BASE_URL}/api/v1/oauth2/device/code"
TOKEN_ENDPOINT = f"{OAUTH_BASE_URL}/api/v1/oauth2/token"

# DashScope endpoints
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com"
DASHSCOPE_APIKEY_ENDPOINT = f"{DASHSCOPE_BASE_URL}/api/v1/apikey"  # This is speculative

CLIENT_ID = "f0304373b74a44d2b584a3fb70ca9e56"
SCOPE = "openid profile email model.completion"
CREDENTIALS_FILE = Path.home() / ".qwen" / "enhanced_oauth_creds.json"

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
    """Enhanced Qwen OAuth2 client with DashScope API key exchange."""
    
    def __init__(self):
        self._creds = _load_credentials() or {}
        self._dashscope_api_key = None
        self._dashscope_api_key_expiry = 0

    def get_dashscope_api_key(self) -> str:
        """
        Get a valid DashScope API key, exchanging OAuth token if necessary.
        First checks if we have a cached valid API key, then tries to exchange
        the OAuth token for one.
        """
        # Check if we have a cached valid DashScope API key
        if self._dashscope_api_key and time.time() < self._dashscope_api_key_expiry:
            return self._dashscope_api_key
            
        # Get a valid OAuth token first
        oauth_token = self.get_access_token()
        
        # Try to exchange OAuth token for DashScope API key
        try:
            api_key = self._exchange_oauth_for_dashscope_key(oauth_token)
            # Cache the API key for 1 hour (3600 seconds)
            self._dashscope_api_key = api_key
            self._dashscope_api_key_expiry = time.time() + 3600
            return api_key
        except Exception as e:
            # If exchange fails, fall back to using the OAuth token directly
            # with the proper headers
            print(f"Warning: Could not exchange OAuth token for DashScope API key: {e}")
            print("Falling back to using OAuth token directly with DashScope headers")
            return oauth_token

    def get_access_token(self) -> str:
        """Get a valid OAuth access token, refreshing if necessary."""
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
        # Don't save credentials to file for testing purposes
        # _save_credentials(self._creds)

    def _exchange_oauth_for_dashscope_key(self, oauth_token: str) -> str:
        """
        Attempt to exchange OAuth token for DashScope API key.
        This is speculative as the exact endpoint is not documented.
        """
        # This is a speculative implementation - we'll try a few common patterns
        possible_endpoints = [
            f"{DASHSCOPE_BASE_URL}/api/v1/user/apikeys",
            f"{DASHSCOPE_BASE_URL}/api/v1/apikey",
            f"{OAUTH_BASE_URL}/api/v1/user/apikeys",
            f"{OAUTH_BASE_URL}/api/v1/apikey"
        ]
        
        headers = {
            "Authorization": f"Bearer {oauth_token}",
            "Content-Type": "application/json",
            "User-Agent": "Qwen-Code-CLI/1.0"
        }
        
        for endpoint in possible_endpoints:
            try:
                # Try GET request first
                r = httpx.get(endpoint, headers=headers, timeout=10.0)
                if r.status_code == 200:
                    try:
                        response_data = r.json()
                        # Look for apikey or similar in response
                        if isinstance(response_data, dict):
                            # Check common key names for API keys
                            for key in ['apikey', 'api_key', 'apiKey', 'data', 'keys']:
                                if key in response_data:
                                    api_key_data = response_data[key]
                                    if isinstance(api_key_data, str):
                                        return api_key_data
                                    elif isinstance(api_key_data, list) and len(api_key_data) > 0:
                                        # If it's a list, return the first key
                                        first_key = api_key_data[0]
                                        if isinstance(first_key, str):
                                            return first_key
                                        elif isinstance(first_key, dict) and 'apikey' in first_key:
                                            return first_key['apikey']
                        # If we get here, try to return the whole response as string
                        return str(response_data)
                    except json.JSONDecodeError:
                        # If not JSON, return text content
                        return r.text
                elif r.status_code not in [404, 405]:  # Don't raise for not found or method not allowed
                    r.raise_for_status()
            except Exception:
                # Continue to next endpoint
                continue
                
            try:
                # Try POST request
                r = httpx.post(endpoint, headers=headers, timeout=10.0)
                if r.status_code == 200:
                    try:
                        response_data = r.json()
                        # Look for apikey or similar in response
                        if isinstance(response_data, dict):
                            # Check common key names for API keys
                            for key in ['apikey', 'api_key', 'apiKey', 'data', 'keys']:
                                if key in response_data:
                                    api_key_data = response_data[key]
                                    if isinstance(api_key_data, str):
                                        return api_key_data
                                    elif isinstance(api_key_data, list) and len(api_key_data) > 0:
                                        # If it's a list, return the first key
                                        first_key = api_key_data[0]
                                        if isinstance(first_key, str):
                                            return first_key
                                        elif isinstance(first_key, dict) and 'apikey' in first_key:
                                            return first_key['apikey']
                        # If we get here, try to return the whole response as string
                        return str(response_data)
                    except json.JSONDecodeError:
                        # If not JSON, return text content
                        return r.text
                elif r.status_code not in [404, 405]:  # Don't raise for not found or method not allowed
                    r.raise_for_status()
            except Exception:
                # Continue to next endpoint
                continue
        
        # If we get here, we couldn't find a working endpoint
        raise Exception("Could not exchange OAuth token for DashScope API key - no working endpoint found")