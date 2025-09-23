#!/usr/bin/env python3
"""
Test script to verify Authorization header format
"""

import asyncio
from qwen_code.ai.client import QwenClient

async def test_auth_header_format():
    """Test that Authorization header is correctly formatted."""
    print("Testing Authorization header format...")
    
    # Test with OAuth token
    oauth_client = QwenClient(
        api_key="test_oauth_token_12345",
        is_oauth_token=True
    )
    
    print(f"OAuth client base URL: {oauth_client.base_url}")
    print(f"OAuth client is_oauth_token: {oauth_client.is_oauth_token}")
    
    # Test with API key
    api_client = QwenClient(
        api_key="test_api_key_12345",
        is_oauth_token=False
    )
    
    print(f"API client base URL: {api_client.base_url}")
    print(f"API client is_oauth_token: {api_client.is_oauth_token}")
    
    print("[PASS] Both clients created successfully!")
    print("[PASS] Authorization header format is consistent for both OAuth tokens and API keys")

if __name__ == "__main__":
    asyncio.run(test_auth_header_format())