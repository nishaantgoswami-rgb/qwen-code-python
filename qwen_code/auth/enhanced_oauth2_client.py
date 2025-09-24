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

# OAuth2 endpoints as specified in the API documentation
OAUTH_BASE_URL = "https://chat.qwen.ai"
TOKEN_ENDPOINT = f"{OAUTH_BASE_URL}/api/v1/oauth2/token"
DEVICE_CODE_ENDPOINT = f"{OAUTH_BASE_URL}/api/v1/oauth2/device/code"

# Corrected DashScope endpoints based on API specification
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com"
# Use the compatible mode endpoint as per the API spec
DASHSCOPE_APIKEY_ENDPOINT = f"{DASHSCOPE_BASE_URL}/compatible-mode/v1/apikey"

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

# OAuth2 endpoints as specified in the API documentation
OAUTH_BASE_URL = "https://chat.qwen.ai"
TOKEN_ENDPOINT = f"{OAUTH_BASE_URL}/api/v1/oauth2/token"
DEVICE_CODE_ENDPOINT = f"{OAUTH_BASE_URL}/api/v1/oauth2/device/code"

# DashScope endpoints
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com"
DASHSCOPE_APIKEY_ENDPOINT = f"{DASHSCOPE_BASE_URL}/compatible-mode/v1/apikey"

# Client configuration - these values should come from environment/config
DEFAULT_CLIENT_ID = os.getenv("QWEN_CLIENT_ID", "f0304373b74a44d2b584a3fb70ca9e56")
DEFAULT_REDIRECT_URI = os.getenv("QWEN_REDIRECT_URI", "http://localhost:8080/callback")
DEFAULT_SCOPE = "openid profile email model.completion"

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
    """Enhanced Qwen OAuth2 client with DashScope API key exchange."""
    
    def __init__(self, client_id: Optional[str] = None, redirect_uri: Optional[str] = None):
        self.client_id = client_id or DEFAULT_CLIENT_ID
        self.redirect_uri = redirect_uri or DEFAULT_REDIRECT_URI
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
                print("Refreshing access token...")
                self._refresh_token()
                return self._creds["access_token"]
            except Exception as e:
                print(f"Token refresh failed: {e}")
                # If refresh fails, fall through to device flow
                pass
        
        # Otherwise do device flow
        print("Starting device flow authentication...")
        return self._device_flow()

    def _device_flow(self) -> str:
        """Perform device code flow authentication with improved error handling."""
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
            "User-Agent": "Qwen-Code-CLI/2.0.0"
        }
        
        with httpx.Client(timeout=30.0) as client:
            try:
                print(f"Requesting device code from: {DEVICE_CODE_ENDPOINT}")
                response = client.post(DEVICE_CODE_ENDPOINT, data=data, headers=headers)
                
                if response.status_code != 200:
                    error_text = response.text
                    print(f"Device code request failed with status {response.status_code}: {error_text}")
                    raise Exception(f"Device code request failed: {response.status_code} - {error_text}")
                
                device = response.json()
                print(f"Device code received. User code: {device.get('user_code', 'N/A')}")
                
                # Open browser and display instructions
                auth_url = device.get('verification_uri_complete', device.get('verification_uri', 'N/A'))
                print(f"Visit: {auth_url}")
                print(f"Enter code: {device.get('user_code', 'N/A')}")
                
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
                        "User-Agent": "Qwen-Code-CLI/2.0.0"
                    }
                    
                    print(f"Polling for token... (attempt at {time.strftime('%H:%M:%S')})")
                    resp = client.post(TOKEN_ENDPOINT, data=payload, headers=headers)
                    
                    if resp.status_code == 200:
                        token_data = resp.json()
                        print("Successfully received access token")
                        break
                    elif resp.status_code == 400:
                        # Handle the case where the user hasn't authorized yet
                        try:
                            error_response = resp.json()
                            err = error_response.get("error")
                            error_description = error_response.get("error_description", "")
                        except json.JSONDecodeError:
                            err = "unknown_error"
                            error_description = resp.text
                        if err not in ("authorization_pending", "slow_down"):
                            print(f"Token exchange failed: {err} - {error_description}")
                            raise Exception(f"Token exchange failed: {err} - {error_description}")
                        if err == "slow_down":
                            interval += 2
                            print("Slowing down polling interval...")
                    else:
                        # For other error codes, raise an exception
                        print(f"Token exchange failed with status {resp.status_code}: {resp.text}")
                        raise Exception(f"Token exchange failed with status {resp.status_code}: {resp.text}")
                else:
                    raise TimeoutError("Device authorization timed out")

                self._store_token_data(token_data)
                return token_data["access_token"]
            except httpx.TimeoutException:
                print("Request timed out - check your network connection")
                raise
            except Exception as e:
                print(f"Device flow failed: {e}")
                raise

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
            "User-Agent": "Qwen-Code-CLI/2.0.0"
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(TOKEN_ENDPOINT, data=payload, headers=headers)
            if response.status_code != 200:
                print(f"Token refresh failed with status {response.status_code}: {response.text}")
                raise Exception(f"Token refresh failed: {response.status_code} - {response.text}")
            data = response.json()
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

    def _exchange_oauth_for_dashscope_key(self, oauth_token: str) -> str:
        """
        Attempt to exchange OAuth token for DashScope API key with improved error handling.
        """
        # Use the proper endpoint as defined in the API documentation
        headers = {
            "Authorization": f"Bearer {oauth_token}",
            "Content-Type": "application/json",
            "User-Agent": "Qwen-Code-CLI/2.0.0"
        }
        
        # First try the compatible-mode API key exchange endpoint
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    DASHSCOPE_APIKEY_ENDPOINT,  # Use the defined constant
                    headers=headers
                )
                if response.status_code == 200:
                    response_data = response.json()
                    # Look for apikey in response
                    if isinstance(response_data, dict):
                        # Check common key names for API keys
                        for key in ['apikey', 'api_key', 'apiKey', 'data']:
                            if key in response_data:
                                api_key_data = response_data[key]
                                if isinstance(api_key_data, str):
                                    print("Successfully exchanged OAuth token for DashScope API key")
                                    return api_key_data
                                elif isinstance(api_key_data, dict) and 'api_key' in api_key_data:
                                    print("Successfully exchanged OAuth token for DashScope API key")
                                    return api_key_data['api_key']
                elif response.status_code == 404:
                    # If the endpoint doesn't exist, try alternative endpoints
                    print("Compatible-mode API key endpoint not found, trying alternatives...")
                    pass
                elif response.status_code == 401:
                    print("Unauthorized: OAuth token may have insufficient permissions for API key exchange")
                    pass
                else:
                    print(f"API key exchange failed with status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Exception during API key exchange: {str(e)}")
            pass  # Continue to alternative endpoints
        
        # Try alternative endpoint based on API spec
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{OAUTH_BASE_URL}/api/v1/user/apikeys",
                    headers=headers
                )
                if response.status_code == 200:
                    response_data = response.json()
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
                                    elif isinstance(first_key, dict) and 'api_key' in first_key:
                                        return first_key['api_key']
                elif response.status_code != 404:
                    print(f"Alternative API key endpoint failed with status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Exception during alternative API key exchange: {str(e)}")
            pass  # Continue to next endpoint
        
        # Try DashScope API key endpoint
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{DASHSCOPE_BASE_URL}/api/v1/user/apikeys",
                    headers=headers
                )
                if response.status_code == 200:
                    response_data = response.json()
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
                                    elif isinstance(first_key, dict) and 'api_key' in first_key:
                                        return first_key['api_key']
                elif response.status_code != 404:
                    print(f"DashScope API key endpoint failed with status {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Exception during DashScope API key exchange: {str(e)}")
            pass  # Continue if endpoint is not available
        
        # If no API key exchange endpoint works, return the OAuth token directly
        # This allows the system to proceed with OAuth token authentication
        print("Using OAuth token directly as API key exchange failed")
        return oauth_token

# Client configuration - these values should come from environment/config
DEFAULT_CLIENT_ID = os.getenv("QWEN_CLIENT_ID", "f0304373b74a44d2b584a3fb70ca9e56")
DEFAULT_REDIRECT_URI = os.getenv("QWEN_REDIRECT_URI", "http://localhost:8080/callback")
DEFAULT_SCOPE = "openid profile email model.completion"

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
    """Enhanced Qwen OAuth2 client with DashScope API key exchange."""
    
    def __init__(self, client_id: Optional[str] = None, redirect_uri: Optional[str] = None):
        self.client_id = client_id or DEFAULT_CLIENT_ID
        self.redirect_uri = redirect_uri or DEFAULT_REDIRECT_URI
        self._creds = _load_credentials() or {}
        self._dashscope_api_key = None
        self._dashscope_api_key_expiry = 0
    
    def clear_cache(self):
        """Clear cached credentials and API key."""
        self._creds = {}
        self._dashscope_api_key = None
        self._dashscope_api_key_expiry = 0
        # Remove credentials file as well
        if CREDENTIALS_FILE.exists():
            try:
                CREDENTIALS_FILE.unlink()  # Delete the file
            except Exception:
                pass  # Ignore errors when deleting the file

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
        
        # Debug logging
        print(f"DEBUG: Requesting device code from {DEVICE_CODE_ENDPOINT}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(DEVICE_CODE_ENDPOINT, data=data, headers=headers)
            if response.status_code != 200:
                print(f"DEBUG: Device code request failed with status {response.status_code}")
                print(f"DEBUG: Response: {response.text}")
                raise Exception(f"Device code request failed with status {response.status_code}: {response.text}")
            device = response.json()
            
            print(f"DEBUG: Device code request successful")
            print(f"Visit: {device['verification_uri_complete']}")
            expiry = time.time() + device["expires_in"]
            interval = device.get("interval", 5)

            # Debug logging
            print(f"DEBUG: Polling for token until {time.strftime('%H:%M:%S', time.localtime(expiry))}")
            
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
                print(f"DEBUG: Token exchange attempt - Status: {resp.status_code}")
                
                if resp.status_code == 200:
                    print(f"DEBUG: Token exchange successful")
                    token_data = resp.json()
                    break
                elif resp.status_code == 400:
                    # Handle the case where the user hasn't authorized yet
                    try:
                        error_response = resp.json()
                        err = error_response.get("error")
                        error_description = error_response.get("error_description", "")
                        print(f"DEBUG: Token exchange 400 error: {err} - {error_description}")
                    except json.JSONDecodeError:
                        err = "unknown_error"
                        error_description = resp.text
                        print(f"DEBUG: Token exchange 400 error (non-JSON): {error_description}")
                    if err not in ("authorization_pending", "slow_down"):
                        raise Exception(f"Token exchange failed: {err} - {error_description}")
                    if err == "slow_down":
                        interval += 2
                else:
                    # For other error codes, raise an exception
                    print(f"DEBUG: Token exchange failed with status {resp.status_code}: {resp.text}")
                    raise Exception(f"Token exchange failed with status {resp.status_code}: {resp.text}")
            else:
                print(f"DEBUG: Device authorization timed out")
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
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(TOKEN_ENDPOINT, data=payload, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Token refresh failed with status {response.status_code}: {response.text}")
            data = response.json()
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

    def _exchange_oauth_for_dashscope_key(self, oauth_token: str) -> str:
        """
        Attempt to exchange OAuth token for DashScope API key.
        """
        # Use the proper endpoint as defined in the API documentation
        headers = {
            "Authorization": f"Bearer {oauth_token}",
            "Content-Type": "application/json",
            "User-Agent": "Qwen-Code-CLI/1.0"
        }
        
        # First try the compatible-mode API key exchange endpoint
        try:
            with httpx.Client() as client:
                response = client.post(
                    DASHSCOPE_APIKEY_ENDPOINT,  # Use the defined constant
                    headers=headers,
                    timeout=10.0
                )
                if response.status_code == 200:
                    response_data = response.json()
                    # Look for apikey in response
                    if isinstance(response_data, dict):
                        # Check common key names for API keys
                        for key in ['apikey', 'api_key', 'apiKey', 'data']:
                            if key in response_data:
                                api_key_data = response_data[key]
                                if isinstance(api_key_data, str):
                                    return api_key_data
                                elif isinstance(api_key_data, dict) and 'api_key' in api_key_data:
                                    return api_key_data['api_key']
                elif response.status_code == 404:
                    # If the endpoint doesn't exist, try alternative endpoints
                    print("Compatible-mode API key endpoint not found, trying alternatives...")
                    pass
                elif response.status_code == 401:
                    print("Unauthorized: OAuth token may have insufficient permissions for API key exchange")
                    pass
                else:
                    print(f"API key exchange failed with status {response.status_code}: {response.text}")
                    # Don't raise an exception here as we'll fall back to using the OAuth token directly
        except Exception as e:
            print(f"Exception during API key exchange: {str(e)}")
            pass  # Continue to alternative endpoints
        
        # Try alternative endpoint based on API spec
        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{OAUTH_BASE_URL}/api/v1/user/apikeys",
                    headers=headers,
                    timeout=10.0
                )
                if response.status_code == 200:
                    response_data = response.json()
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
                                    elif isinstance(first_key, dict) and 'api_key' in first_key:
                                        return first_key['api_key']
                elif response.status_code != 404:
                    response.raise_for_status()
        except Exception:
            pass  # Continue to next endpoint
        
        # Try DashScope API key endpoint
        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{DASHSCOPE_BASE_URL}/api/v1/user/apikeys",
                    headers=headers,
                    timeout=10.0
                )
                if response.status_code == 200:
                    response_data = response.json()
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
                                    elif isinstance(first_key, dict) and 'api_key' in first_key:
                                        return first_key['api_key']
                elif response.status_code != 404:
                    response.raise_for_status()
        except Exception:
            pass  # Continue if endpoint is not available
        
        # If no API key exchange endpoint works, return the OAuth token directly
        # This allows the system to proceed with OAuth token authentication
        return oauth_token