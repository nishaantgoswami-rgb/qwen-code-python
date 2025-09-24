"""
Comprehensive fixes for Qwen OAuth authentication issues.

This module addresses the authentication problems where the system defaults to 
'openai_compatible' provider with no API key but then tries to authenticate 
using Qwen OAuth device code flow with client=qwen-code, resulting in 400 
Bad Request errors.
"""

import httpx
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# OAuth2 endpoints as specified in the API documentation
OAUTH_BASE_URL = "https://chat.qwen.ai"
TOKEN_ENDPOINT = f"{OAUTH_BASE_URL}/api/v1/oauth2/token"
DEVICE_CODE_ENDPOINT = f"{OAUTH_BASE_URL}/api/v1/oauth2/device/code"

# Client configuration
DEFAULT_CLIENT_ID = "f0304373b74a44d2b584a3fb70ca9e56"  # Updated client ID
DEFAULT_REDIRECT_URI = "http://localhost:8080/callback"
DEFAULT_SCOPE = "openid profile email model.completion"


class QwenOAuth2ClientFixed:
    """
    Fixed Qwen OAuth2 client to resolve authentication issues.
    """
    
    def __init__(self, client_id: Optional[str] = None, redirect_uri: Optional[str] = None):
        self.client_id = client_id or DEFAULT_CLIENT_ID
        self.redirect_uri = redirect_uri or DEFAULT_REDIRECT_URI
        self._creds = self._load_credentials() or {}
        self._dashscope_api_key = None
        self._dashscope_api_key_expiry = 0

    def _load_credentials(self) -> Optional[Dict[str, Any]]:
        """Load credentials from JSON file."""
        from pathlib import Path
        import json
        credentials_file = Path.home() / ".qwen" / "enhanced_oauth_creds.json"
        if credentials_file.exists():
            try:
                with open(credentials_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def get_access_token(self) -> str:
        """
        Get a valid access token with proper error handling.
        """
        # Check if we have a valid access token
        if self._creds.get("access_token") and self._creds.get("expiry", 0) > self._get_current_timestamp():
            print("Using cached access token")
            return self._creds["access_token"]
        
        # Attempt refresh if expired and refresh token exists
        if self._creds.get("refresh_token"):
            try:
                print("Attempting to refresh token...")
                self._refresh_token()
                return self._creds["access_token"]
            except Exception as e:
                print(f"Token refresh failed: {e}")
                # If refresh fails, fall through to device flow
        
        # Otherwise do device flow
        print("Starting device flow authentication...")
        return self._device_flow()

    def _get_current_timestamp(self) -> float:
        """Get current timestamp."""
        return datetime.now().timestamp()

    def _device_flow(self) -> str:
        """
        Fixed device code flow with proper headers and parameters.
        """
        import base64
        import hashlib
        import os
        import time
        
        # Generate PKCE parameters
        def _generate_pkce_pair():
            verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
            digest = hashlib.sha256(verifier.encode()).digest()
            challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
            return verifier, challenge
        
        verifier, challenge = _generate_pkce_pair()
        
        # Device code request data and headers
        device_data = {
            "client_id": self.client_id,
            "scope": DEFAULT_SCOPE,
            "code_challenge": challenge,
            "code_challenge_method": "S256"
        }
        
        # Proper headers for device code request
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Qwen-Code-CLI/2.0.0"
        }
        
        print(f"Requesting device code from: {DEVICE_CODE_ENDPOINT}")
        
        with httpx.Client() as client:
            try:
                response = client.post(DEVICE_CODE_ENDPOINT, data=device_data, headers=headers, timeout=30.0)
                print(f"Device code request response: {response.status_code}")
                
                if response.status_code != 200:
                    error_text = response.text
                    print(f"Device code request failed with status {response.status_code}: {error_text}")
                    raise Exception(f"Device code request failed: {error_text}")
                
                device = response.json()
                print(f"Received device code: {device.get('device_code', 'N/A')[:10]}")
                
                # Open browser and display instructions
                auth_url = device.get('verification_uri_complete', device.get('verification_uri', 'N/A'))
                print(f"Visit: {auth_url}")
                print(f"User code: {device.get('user_code', 'N/A')}")
                
                # Attempt to open the browser automatically
                try:
                    import webbrowser
                    webbrowser.open(auth_url)
                except Exception as e:
                    print(f"Could not automatically open browser: {e}")
                    print("Please manually open the URL in your browser.")
                
                expiry = time.time() + device.get("expires_in", 900)  # Default to 15 minutes
                interval = device.get("interval", 5)
                
                # Poll for token
                while time.time() < expiry:
                    time.sleep(interval)
                    
                    # Token exchange request data
                    token_data = {
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                        "device_code": device["device_code"],
                        "client_id": self.client_id,
                        "code_verifier": verifier
                    }
                    
                    # Proper headers for token exchange
                    token_headers = {
                        "Content-Type": "application/x-www-form-urlencoded",
                        "User-Agent": "Qwen-Code-CLI/2.0.0"
                    }
                    
                    print(f"Polling for token at: {TOKEN_ENDPOINT}")
                    resp = client.post(TOKEN_ENDPOINT, data=token_data, headers=token_headers, timeout=30.0)
                    print(f"Token polling response: {resp.status_code}")
                    
                    if resp.status_code == 200:
                        token_data = resp.json()
                        print("Successfully received token")
                        self._store_token_data(token_data)
                        return token_data["access_token"]
                    
                    # Parse error response
                    try:
                        error_resp = resp.json()
                        error = error_resp.get("error", "unknown_error")
                    except json.JSONDecodeError:
                        error = "invalid_response"
                    
                    if error not in ("authorization_pending", "slow_down"):
                        error_desc = error_resp.get("error_description", "Unknown error")
                        print(f"Authentication failed: {error} - {error_desc}")
                        raise Exception(f"Device flow failed: {error} - {error_desc}")
                    
                    if error == "slow_down":
                        interval += 2  # Increase polling interval
                
                raise TimeoutError("Device authorization timed out")
                
            except httpx.TimeoutException:
                print("Request timed out")
                raise
            except Exception as e:
                print(f"Device flow failed: {e}")
                raise

    def _refresh_token(self) -> None:
        """
        Fixed token refresh with proper error handling.
        """
        refresh_data = {
            "grant_type": "refresh_token",
            "refresh_token": self._creds["refresh_token"],
            "client_id": self.client_id
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Qwen-Code-CLI/2.0.0"
        }
        
        with httpx.Client() as client:
            response = client.post(TOKEN_ENDPOINT, data=refresh_data, headers=headers, timeout=30.0)
            
            if response.status_code != 200:
                print(f"Token refresh failed with status {response.status_code}: {response.text}")
                raise Exception(f"Token refresh failed: {response.status_code} - {response.text}")
            
            data = response.json()
            self._store_token_data(data)

    def _store_token_data(self, data: Dict[str, Any]) -> None:
        """
        Store token data with proper expiration handling.
        """
        from pathlib import Path
        import json
        
        self._creds = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", self._creds.get("refresh_token")),
            "expiry": datetime.now().timestamp() + data.get("expires_in", 3600),
            # Store resource_url if provided
            "resource_url": data.get("resource_url")
        }
        
        # Save credentials
        credentials_file = Path.home() / ".qwen" / "enhanced_oauth_creds.json"
        credentials_file.parent.mkdir(parents=True, exist_ok=True)
        with open(credentials_file, 'w') as f:
            json.dump(self._creds, f)
        
        print("Tokens saved to credentials file")


class QwenOAuthProviderFixed:
    """
    Fixed Qwen OAuth provider with improved error handling and token management.
    """
    
    def __init__(self, client_id: str, redirect_uri: str, client_secret: Optional[str] = None):
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.client_secret = client_secret
        self.auth_base_url = "https://chat.qwen.ai"
        # Use the correct OAuth2 endpoints as per API specification
        self.api_base_url = f"{self.auth_base_url}/api/v1/oauth2"
        self.token_url = f"{self.api_base_url}/token"
        self.authorize_url = f"{self.auth_base_url}/oauth2/authorize"
        self.device_code_url = f"{self.api_base_url}/device/code"
        self._credentials = None
    
    async def authenticate(self, use_device_flow: bool = True) -> dict:
        """
        Fixed authenticate method with better error handling.
        """
        try:
            if use_device_flow:
                # Use the fixed client
                oauth_client = QwenOAuth2ClientFixed(client_id=self.client_id, redirect_uri=self.redirect_uri)
                access_token = oauth_client.get_access_token()
                
                # Calculate expiration time
                from datetime import datetime, timedelta
                expires_at = datetime.now() + timedelta(hours=1)  # Default to 1 hour if not in credentials
                
                # Try to get from credentials if possible
                try:
                    from pathlib import Path
                    import json
                    credentials_file = Path.home() / ".qwen" / "enhanced_oauth_creds.json"
                    if credentials_file.exists():
                        with open(credentials_file, 'r') as f:
                            creds_data = json.load(f)
                            if 'expiry' in creds_data:
                                expires_at = datetime.fromtimestamp(creds_data['expiry'])
                except:
                    pass  # Use default expiration
                
                return {
                    "success": True,
                    "access_token": access_token,
                    "refresh_token": self._get_refresh_token(),
                    "expires_at": expires_at
                }
            else:
                # For authorization code flow (web flow), we could implement this differently
                return {
                    "success": False,
                    "error_message": "Web flow authentication not implemented in this version"
                }
        except Exception as e:
            print(f"Authentication failed: {str(e)}")
            return {
                "success": False,
                "error_message": f"Authentication failed: {str(e)}"
            }
    
    def _get_refresh_token(self):
        """
        Get refresh token from stored credentials if available.
        """
        try:
            from pathlib import Path
            import json
            credentials_file = Path.home() / ".qwen" / "enhanced_oauth_creds.json"
            if credentials_file.exists():
                with open(credentials_file, 'r') as f:
                    creds_data = json.load(f)
                    return creds_data.get('refresh_token')
        except:
            pass
        return None


def validate_config():
    """
    Validate the authentication configuration.
    """
    print("Validating authentication configuration...")
    
    # Check if required environment variables are set
    import os
    client_id = os.getenv("QWEN_CLIENT_ID", DEFAULT_CLIENT_ID)
    redirect_uri = os.getenv("QWEN_REDIRECT_URI", DEFAULT_REDIRECT_URI)
    
    print(f"Client ID: {client_id[:10] if client_id else 'NOT SET'}...")
    print(f"Redirect URI: {redirect_uri}")
    
    # Test connectivity to OAuth endpoints
    try:
        import httpx
        response = httpx.get(f"{OAUTH_BASE_URL}/health", timeout=10.0)
        print(f"OAuth server connectivity: {response.status_code if response else 'FAILED'}")
    except Exception as e:
        print(f"OAuth server connectivity: FAILED - {e}")
    
    return True


if __name__ == "__main__":
    # Example usage of the fixed OAuth client
    print("Testing fixed OAuth authentication...")
    
    validate_config()
    
    # Test the fixed OAuth client
    try:
        oauth_client = QwenOAuth2ClientFixed()
        token = oauth_client.get_access_token()
        print(f"Successfully obtained token: {token[:20]}...")
    except Exception as e:
        print(f"Failed to get token: {e}")