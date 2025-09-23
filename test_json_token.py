#!/usr/bin/env python3
"""
Test using the token from the JSON file instead of the encrypted database
"""

import asyncio
from qwen_code.auth.credentials import CredentialManager
from qwen_code.ai.client import QwenClient

async def test_json_token():
    """Test using the token from the JSON file."""
    print("Testing with token from JSON file...")
    
    # Load credentials from JSON file (the format that the OAuth client uses)
    cred_manager = CredentialManager()
    json_creds = cred_manager.load_tokens_from_json()
    
    if not json_creds or not json_creds.get('access_token'):
        print("[FAIL] No OAuth credentials found in JSON file")
        return
    
    access_token = json_creds['access_token']
    print(f"Access token from JSON: {access_token[:50]}...")
    print(f"Token type: {json_creds.get('token_type', 'Unknown')}")
    
    # Create AI client with OAuth token
    ai_client = QwenClient(
        api_key=access_token,
        is_oauth_token=True
    )
    
    # Test a simple chat request
    print("Sending test request...")
    try:
        from qwen_code.ai.client import Message
        messages = [Message(role="user", content="Hello, this is a test message.")]
        response = await ai_client.chat(messages, max_tokens=50)
        print("[SUCCESS] API request successful!")
        print(f"Response: {response.content[:100]}...")
    except Exception as e:
        print(f"[FAIL] API request failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_json_token())