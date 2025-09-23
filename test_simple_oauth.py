#!/usr/bin/env python3
"""
Simple test script to verify OAuth implementation fixes without Unicode characters
"""

import asyncio
import json
from pathlib import Path
from qwen_code.auth.providers import QwenOAuthProvider
from qwen_code.auth.credentials import CredentialManager
from qwen_code.ai.client import QwenClient
from qwen_code.config.settings import Config

async def test_credential_loading():
    """Test that credentials can be loaded from both storage mechanisms."""
    print("Testing credential loading...")
    
    # Test loading from encrypted database
    cred_manager = CredentialManager()
    credentials = cred_manager.load_credentials("qwen_oauth")
    print(f"Credentials from database: {credentials is not None}")
    if credentials:
        print(f"  Access token: {credentials.access_token[:20] if credentials.access_token else 'None'}...")
        print(f"  Expires at: {credentials.expires_at}")
    
    # Test loading from JSON file
    json_creds = cred_manager.load_tokens_from_json()
    print(f"Credentials from JSON: {len(json_creds) > 0}")
    if json_creds:
        print(f"  Access token: {json_creds.get('access_token', '')[:20] if json_creds.get('access_token') else 'None'}...")
        print(f"  Expires at: {json_creds.get('expires_at')}")
    
    return credentials or (json_creds if json_creds.get('access_token') else None)

async def test_oauth_provider():
    """Test OAuth provider functionality."""
    print("\nTesting OAuth provider...")
    
    # Create OAuth provider
    config = Config()
    await config.load()
    provider_config = config.providers.get("qwen_oauth")
    
    if not provider_config:
        print("No Qwen OAuth provider configured")
        return
    
    provider = QwenOAuthProvider(
        client_id=provider_config.client_id or "f0304373b74a44d2b584a3fb70ca9e56",
        redirect_uri=provider_config.redirect_uri or "http://localhost:8080/callback",
        client_secret=provider_config.client_secret
    )
    
    # Test credential validation
    print(f"Provider has valid credentials: {provider.is_valid()}")
    print(f"Provider has valid cached credentials: {provider.has_valid_cached_credentials()}")

async def test_ai_client():
    """Test AI client with OAuth token."""
    print("\nTesting AI client...")
    
    # Load credentials
    cred_manager = CredentialManager()
    
    # Try database first
    credentials = cred_manager.load_credentials("qwen_oauth")
    api_key = None
    is_oauth_token = False
    
    if credentials and credentials.access_token:
        api_key = credentials.access_token
        is_oauth_token = True
        print("Using credentials from database")
    else:
        # Fallback to JSON
        json_creds = cred_manager.load_tokens_from_json()
        if json_creds and json_creds.get('access_token'):
            api_key = json_creds['access_token']
            is_oauth_token = True
            print("Using credentials from JSON file")
    
    if api_key:
        # Create AI client
        ai_client = QwenClient(
            api_key=api_key,
            is_oauth_token=is_oauth_token
        )
        
        print(f"AI client created successfully")
        print(f"  Base URL: {ai_client.base_url}")
        print(f"  Is OAuth token: {ai_client.is_oauth_token}")
        
        # Test token validation
        validated_token = await ai_client._ensure_valid_token()
        print(f"Validated token: {validated_token[:20] if validated_token else 'None'}...")
    else:
        print("No credentials found")

async def main():
    """Main test function."""
    print("=== OAuth Implementation Fix Verification ===")
    print()
    
    # Test credential loading
    credentials = await test_credential_loading()
    
    # Test OAuth provider
    await test_oauth_provider()
    
    # Test AI client
    await test_ai_client()
    
    print()
    print("=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(main())