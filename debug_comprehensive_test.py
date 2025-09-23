#!/usr/bin/env python3
"""
Comprehensive test script for the Qwen chat endpoint implementation.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qwen_code.ai.client import QwenClient, Message
from qwen_code.auth.providers import QwenOAuthProvider
from qwen_code.auth.credentials import CredentialManager
from qwen_code.config.settings import Config


async def test_comprehensive_flow():
    """Test the complete flow from authentication to chat completion."""
    print("=== Comprehensive Qwen Chat Endpoint Test ===")
    
    # Step 1: Load configuration
    print("\n1. Loading configuration...")
    config = Config()
    await config.load()
    
    provider_config = config.providers.get("qwen_oauth")
    if not provider_config:
        print("Error: Qwen OAuth provider configuration not found")
        return
    
    print(f"Client ID: {provider_config.client_id}")
    print(f"Redirect URI: {provider_config.redirect_uri}")
    
    # Step 2: Create OAuth provider
    print("\n2. Creating OAuth provider...")
    oauth_provider = QwenOAuthProvider(
        client_id=provider_config.client_id or "f0304373b74a44d2b584a3fb70ca9e56",
        redirect_uri=provider_config.redirect_uri or "http://localhost:8080/callback",
        client_secret=provider_config.client_secret
    )
    
    # Step 3: Check credential status
    print("\n3. Checking credential status...")
    has_valid_creds = oauth_provider.is_valid()
    print(f"Has valid credentials: {has_valid_creds}")
    
    if has_valid_creds:
        credentials = oauth_provider.get_credentials()
        print(f"Access token: {credentials.access_token[:10] if credentials.access_token else None}...")
        if credentials.expires_at:
            print(f"Token expires at: {credentials.expires_at}")
    
    # Step 4: Test token refresh
    print("\n4. Testing token refresh...")
    refresh_result = await oauth_provider.refresh_token()
    
    if refresh_result.success:
        print("Token refresh successful!")
        print(f"New access token: {refresh_result.access_token[:10]}...")
    else:
        print(f"Token refresh failed: {refresh_result.error_message}")
        # If refresh failed, try to authenticate
        print("Attempting full authentication...")
        auth_result = await oauth_provider.authenticate()
        if not auth_result.success:
            print(f"Authentication failed: {auth_result.error_message}")
            return
        print("Authentication successful!")
    
    # Step 5: Create Qwen client
    print("\n5. Creating Qwen client...")
    credentials = oauth_provider.get_credentials()
    if not credentials or not credentials.access_token:
        print("Error: No access token available")
        return
    
    client = QwenClient(
        api_key=credentials.access_token,
        model="qwen3-coder-plus",
        is_oauth_token=True
    )
    
    # Step 6: Test chat completion
    print("\n6. Testing chat completion...")
    messages = [
        Message(role="user", content="Hello, this is a comprehensive test. Please respond with 'Comprehensive test successful!'")
    ]
    
    try:
        response = await client.chat(messages)
        print(f"Response: {response.content}")
        print(f"Usage: prompt_tokens={response.usage.prompt_tokens}, completion_tokens={response.usage.completion_tokens}")
        print("Chat completion test completed successfully!")
    except Exception as e:
        print(f"Error during chat completion: {e}")
        return
    
    # Step 7: Test streaming chat
    print("\n7. Testing streaming chat...")
    stream_messages = [
        Message(role="user", content="This is a streaming test. Please respond with a short message.")
    ]
    
    try:
        response_text = ""
        async for chunk in client.stream_chat(stream_messages):
            response_text += chunk
        print(f"Streamed response: {response_text}")
        print("Streaming chat test completed successfully!")
    except Exception as e:
        print(f"Error during streaming chat: {e}")
        return
    
    print("\n=== All tests completed successfully! ===")


if __name__ == "__main__":
    asyncio.run(test_comprehensive_flow())