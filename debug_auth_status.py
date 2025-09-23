#!/usr/bin/env python3
"""
Utility script to check and debug authentication status.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qwen_code.auth.providers import QwenOAuthProvider
from qwen_code.auth.credentials import CredentialManager
from qwen_code.config.settings import Config


async def debug_auth_status():
    """Debug authentication status and credentials."""
    print("=== Authentication Status Debug ===")
    
    # Load configuration
    print("\n1. Loading configuration...")
    config = Config()
    await config.load()
    
    provider_config = config.providers.get("qwen_oauth")
    if not provider_config:
        print("Error: Qwen OAuth provider configuration not found")
        return
    
    print(f"Client ID: {provider_config.client_id}")
    print(f"Redirect URI: {provider_config.redirect_uri}")
    print(f"Client Secret: {'*' * 10 if provider_config.client_secret else 'None'}")
    
    # Check credential manager
    print("\n2. Checking credential manager...")
    cred_manager = CredentialManager()
    providers = cred_manager.list_providers()
    print(f"Providers with stored credentials: {providers}")
    
    if "qwen_oauth" in providers:
        print("Found qwen_oauth credentials in database")
        credentials = cred_manager.load_credentials("qwen_oauth")
        if credentials:
            print(f"  Access token: {credentials.access_token[:10] if credentials.access_token else None}...")
            print(f"  Refresh token: {'*' * 10 if credentials.refresh_token else None}")
            print(f"  Expires at: {credentials.expires_at}")
            if credentials.expires_at:
                try:
                    expires_at = datetime.fromisoformat(credentials.expires_at)
                    is_expired = expires_at <= datetime.now()
                    print(f"  Token expired: {is_expired}")
                except ValueError:
                    print("  Error parsing expiration time")
        else:
            print("  Failed to load credentials from database")
    
    # Check JSON file
    print("\n3. Checking JSON credentials...")
    json_creds = cred_manager.load_tokens_from_json()
    if json_creds:
        print("Found credentials in JSON file:")
        print(f"  Access token: {json_creds.get('access_token', '')[:10] if json_creds.get('access_token') else None}...")
        print(f"  Refresh token: {'*' * 10 if json_creds.get('refresh_token') else None}")
        print(f"  Expires at: {json_creds.get('expires_at')}")
        if json_creds.get('expires_at'):
            try:
                expires_at = datetime.fromisoformat(json_creds['expires_at'])
                is_expired = expires_at <= datetime.now()
                print(f"  Token expired: {is_expired}")
            except ValueError:
                print("  Error parsing expiration time")
    else:
        print("No credentials found in JSON file")
    
    # Check OAuth provider
    print("\n4. Checking OAuth provider...")
    oauth_provider = QwenOAuthProvider(
        client_id=provider_config.client_id or "f0304373b74a44d2b584a3fb70ca9e56",
        redirect_uri=provider_config.redirect_uri or "http://localhost:8080/callback",
        client_secret=provider_config.client_secret
    )
    
    is_valid = oauth_provider.is_valid()
    print(f"OAuth provider credentials valid: {is_valid}")
    
    if is_valid:
        credentials = oauth_provider.get_credentials()
        if credentials:
            print(f"  Access token: {credentials.access_token[:10] if credentials.access_token else None}...")
            print(f"  Refresh token: {'*' * 10 if credentials.refresh_token else None}")
            print(f"  Expires at: {credentials.expires_at}")
    
    print("\n=== Debug completed ===")


if __name__ == "__main__":
    asyncio.run(debug_auth_status())
