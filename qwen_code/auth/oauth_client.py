#!/usr/bin/env python3
"""
Qwen OAuth implementation for device code flow
"""

import base64
import hashlib
import os
import time
import httpx
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json

# Qwen.ai OAuth2 endpoints
OAUTH_BASE = "https://chat.qwen.ai"
AUTHORIZE_URL = f"{OAUTH_BASE}/oauth2/authorize"
DEVICE_CODE_URL = f"{OAUTH_BASE}/api/v1/oauth2/device/code"
TOKEN_URL = f"{OAUTH_BASE}/api/v1/oauth2/token"

# Public client ID for Qwen Code CLI
CLIENT_ID = "f0304373b74a44d2b584a3fb70ca9e56"
SCOPE = "openid profile email model.completion"


class QwenOAuthClient:
    """Qwen OAuth client for device code flow."""
    
    def __init__(self, client_id: str = CLIENT_ID):
        self.client_id = client_id
        self.credentials_path = Path.home() / ".qwen" / "oauth_client_creds.json"
    
    def generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE verifier and challenge."""
        # Create a high-entropy verifier
        verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
        digest = hashlib.sha256(verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        return verifier, challenge
    
    def request_device_code(self, verifier: str, challenge: str) -> Dict[str, Any]:
        """Request device code from Qwen OAuth server."""
        data = {
            "client_id": self.client_id,
            "scope": SCOPE,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        
        # Add headers for proper content type
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Qwen-Code-CLI/1.0"
        }
        
        response = httpx.post(DEVICE_CODE_URL, data=data, headers=headers, follow_redirects=False)
        response.raise_for_status()
        return response.json()
    
    def poll_for_token(self, device_code: str, verifier: str, interval: int, expires_in: int) -> Dict[str, Any]:
        """Poll for access token."""
        deadline = time.time() + expires_in
        current_interval = interval
        
        # Add headers for proper content type
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Qwen-Code-CLI/1.0"
        }
        
        while time.time() < deadline:
            data = {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": self.client_id,
                "device_code": device_code,
                "code_verifier": verifier,
            }
            
            response = httpx.post(TOKEN_URL, data=data, headers=headers, follow_redirects=False)
            
            if response.status_code == 200:
                return response.json()  # Success
            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    error = error_data.get("error")
                    
                    if error == "authorization_pending":
                        time.sleep(current_interval)
                        continue
                    elif error == "slow_down":
                        current_interval += 2
                        time.sleep(current_interval)
                        continue
                    else:
                        raise Exception(f"OAuth error: {error}")
                except json.JSONDecodeError:
                    # If we can't decode JSON, raise the original error
                    response.raise_for_status()
            else:
                response.raise_for_status()
        
        raise TimeoutError("Device authorization timed out")
    
    def save_credentials(self, creds: Dict[str, Any]) -> None:
        """Save credentials to JSON file."""
        self.credentials_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.credentials_path, "w") as f:
            json.dump(creds, f)
    
    def load_credentials(self) -> Optional[Dict[str, Any]]:
        """Load credentials from JSON file."""
        if self.credentials_path.exists():
            with open(self.credentials_path, "r") as f:
                return json.load(f)
        return None
    
    def has_valid_credentials(self) -> bool:
        """Check if valid credentials are available."""
        creds = self.load_credentials()
        if not creds:
            return False
        
        # Check if access_token exists
        if not creds.get("access_token"):
            return False
        
        # Check token expiration if available
        if creds.get("expires_at"):
            try:
                expires_at = datetime.fromisoformat(creds["expires_at"])
                # Consider token expired 5 minutes before actual expiration to allow for refresh
                if expires_at <= (datetime.now() + timedelta(minutes=5)):
                    return False
            except ValueError:
                # Invalid date format, treat as expired
                return False
        
        return True
    
    def authenticate(self) -> str:
        """Perform device code flow authentication."""
        # Try cached credentials first
        creds = self.load_credentials()
        if creds and creds.get("access_token"):
            # Check if token is still valid
            if self.has_valid_credentials():
                return creds["access_token"]
        
        # Generate PKCE pair
        verifier, challenge = self.generate_pkce_pair()
        
        # Request device code
        device_data = self.request_device_code(verifier, challenge)
        
        # Display instructions to user
        print("Qwen OAuth Authentication")
        print("=" * 25)
        print(f"Visit: {device_data['verification_uri_complete']}")
        print(f"Or enter code: {device_data['user_code']}")
        print()
        print("Waiting for authorization...")
        
        # Poll for token
        token_data = self.poll_for_token(
            device_code=device_data["device_code"],
            verifier=verifier,
            interval=device_data.get("interval", 5),
            expires_in=device_data["expires_in"]
        )
        
        # Save credentials
        self.save_credentials(token_data)
        
        return token_data["access_token"]


if __name__ == "__main__":
    # Test the OAuth client
    client = QwenOAuthClient()
    try:
        access_token = client.authenticate()
        print(f"Authentication successful!")
        print(f"Access Token: {access_token[:20]}...")
    except Exception as e:
        print(f"Authentication failed: {str(e)}")