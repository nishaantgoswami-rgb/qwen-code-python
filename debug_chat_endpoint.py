#!/usr/bin/env python3
"""
Debug script to test the Qwen chat endpoint implementation.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qwen_code.ai.client import QwenClient, Message
from qwen_code.auth.providers import QwenOAuthProvider
from qwen_code.config.settings import Config


async def test_chat_endpoint():
    """Test the chat endpoint with OAuth token."""
    print("Testing Qwen chat endpoint...")
    
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
    if not oauth_provider.is_valid():
        print("OAuth credentials are not valid. Attempting to authenticate...")
        auth_result = await oauth_provider.authenticate()
        if not auth_result.success:
            print(f"Authentication failed: {auth_result.error_message}")
            return
        print("Authentication successful!")
    
    # Get the access token
    credentials = oauth_provider.get_credentials()
    if not credentials or not credentials.access_token:
        print("Error: No access token available")
        return
    
    print(f"Using access token: {credentials.access_token[:10]}...")
    
    # Create Qwen client with OAuth token
    client = QwenClient(
        api_key=credentials.access_token,
        model="qwen3-coder-plus",
        is_oauth_token=True
    )
    
    # Test chat completion
    messages = [
        Message(role="user", content="Hello, this is a test message. Please respond with 'Test successful!'")
    ]
    
    print("Sending chat request...")
    try:
        response = await client.chat(messages)
        print(f"Response: {response.content}")
        print(f"Usage: {response.usage}")
        print("Chat endpoint test completed successfully!")
    except Exception as e:
        print(f"Error during chat request: {e}")
        return


if __name__ == "__main__":
    asyncio.run(test_chat_endpoint())