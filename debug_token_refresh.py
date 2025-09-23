#!/usr/bin/env python3
"""
Debug script to test OAuth token refresh functionality.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qwen_code.auth.providers import QwenOAuthProvider
from qwen_code.config.settings import Config


async def test_token_refresh():
    """Test the OAuth token refresh functionality."""
    print("Testing OAuth token refresh...")
    
    # Load configuration
    config = Config()
    await config.load()
    
    provider_config = config.providers.get("qwen_oauth")
    if not provider_config:
        print("Error: Qwen OAuth provider configuration not found")
        return
    
    # Create OAuth provider
    oauth_provider = QwenOAuthProvider(
        client_id=provider_config.client_id or "f0304373b74a44d2b584a3fb70ca9e56",
        redirect_uri=provider_config.redirect_uri or "http://localhost:8080/callback",
        client_secret=provider_config.client_secret
    )
    
    # Check if we have valid credentials
    print(f"Current credentials valid: {oauth_provider.is_valid()}")
    
    if oauth_provider.is_valid():
        credentials = oauth_provider.get_credentials()
        print(f"Current access token: {credentials.access_token[:10] if credentials.access_token else None}...")
        print(f"Current refresh token: {'*' * 10 if credentials.refresh_token else None}")
        if credentials.expires_at:
            print(f"Token expires at: {credentials.expires_at}")
    
    # Try to refresh the token
    print("Attempting to refresh token...")
    refresh_result = await oauth_provider.refresh_token()
    
    if refresh_result.success:
        print("Token refresh successful!")
        print(f"New access token: {refresh_result.access_token[:10]}...")
        print(f"New refresh token: {'*' * 10 if refresh_result.refresh_token else None}")
        if refresh_result.expires_at:
            print(f"New token expires at: {refresh_result.expires_at}")
    else:
        print(f"Token refresh failed: {refresh_result.error_message}")


if __name__ == "__main__":
    asyncio.run(test_token_refresh())