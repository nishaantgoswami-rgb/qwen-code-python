#!/usr/bin/env python3
"""
Complete test for OAuth implementation
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the path so we can import our modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from qwen_code.auth.providers import QwenOAuthProvider
from qwen_code.auth.credentials import CredentialManager
from qwen_code.ai.client import QwenClient
from qwen_code.ai.client import Message

async def test_complete_flow():
    """Test the complete authentication and API call flow."""
    print("=== Testing Complete OAuth Flow ===")
    
    # Step 1: Check if we have valid credentials
    cred_manager = CredentialManager()
    has_valid_creds = cred_manager.has_valid_credentials("qwen_oauth")
    print(f"Has valid credentials: {has_valid_creds}")
    
    if not has_valid_creds:
        print("No valid credentials found. Testing authentication...")
        # Step 2: Authenticate
        provider = QwenOAuthProvider(
            client_id="f0304373b74a44d2b584a3fb70ca9e56",
            redirect_uri="http://localhost:8080/callback"
        )
        
        auth_result = await provider.authenticate(use_device_flow=True)
        if not auth_result.success:
            print(f"Authentication failed: {auth_result.error_message}")
            return False
        print("Authentication successful!")
    else:
        print("Using existing valid credentials")
    
    # Step 3: Load credentials
    credentials = cred_manager.load_credentials("qwen_oauth")
    if not credentials or not credentials.access_token:
        print("Failed to load credentials")
        return False
    
    print(f"Using access token: {credentials.access_token[:20]}...")
    
    # Step 4: Create AI client
    ai_client = QwenClient(
        api_key=credentials.access_token,
        is_oauth_token=True
    )
    
    # Step 5: Make a simple API call
    print("Making test API call...")
    try:
        messages = [Message(role="user", content="Hello, this is a test message.")]
        response = await ai_client.chat(messages, max_tokens=50)
        print("API call successful!")
        print(f"Response: {response.content[:100]}...")
        return True
    except Exception as e:
        print(f"API call failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_complete_flow())
    if success:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Tests failed!")
        sys.exit(1)