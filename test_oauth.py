#!/usr/bin/env python3
"""
Test script for Qwen OAuth implementation
"""

import asyncio
from qwen_code.auth.providers import QwenOAuthProvider
from qwen_code.auth.oauth_client import QwenOAuthClient

async def test_oauth_provider():
    """Test OAuth provider implementation."""
    print("Testing OAuth Provider...")
    # Using the public client ID from the OAuth client
    provider = QwenOAuthProvider(
        client_id="f0304373b74a44d2b584a3fb70ca9e56",
        redirect_uri="http://localhost:8080/callback"
    )
    
    # Test authentication (this will likely fail without user interaction)
    try:
        result = await provider.authenticate(use_device_flow=True)
        if result.success:
            print("OAuth Provider Authentication successful!")
            print(f"Access Token: {result.access_token[:20]}...")
        else:
            print(f"OAuth Provider Authentication failed: {result.error_message}")
    except Exception as e:
        print(f"OAuth Provider Authentication error: {str(e)}")

def test_oauth_client():
    """Test OAuth client implementation."""
    print("\nTesting OAuth Client...")
    client = QwenOAuthClient()
    
    # Test PKCE generation
    verifier, challenge = client.generate_pkce_pair()
    print(f"PKCE Verifier: {verifier[:20]}...")
    print(f"PKCE Challenge: {challenge[:20]}...")
    
    # Test credential validation
    print(f"Has valid credentials: {client.has_valid_credentials()}")

if __name__ == "__main__":
    # Test OAuth client
    test_oauth_client()
    
    # Test OAuth provider
    asyncio.run(test_oauth_provider())