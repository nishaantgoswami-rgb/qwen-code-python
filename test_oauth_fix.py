#!/usr/bin/env python3
"""
Test script to verify OAuth implementation fix
"""

import asyncio
import json
from pathlib import Path
from qwen_code.auth.providers import QwenOAuthProvider
from qwen_code.auth.credentials import CredentialManager
from qwen_code.ai.client import QwenClient

async def test_oauth_flow():
    """Test the complete OAuth flow."""
    print("Testing OAuth flow...")
    
    # Create OAuth provider
    provider = QwenOAuthProvider(
        client_id="f0304373b74a44d2b584a3fb70ca9e56",
        redirect_uri="http://localhost:8080/callback"
    )
    
    # Test authentication with device flow
    print("Starting device flow authentication...")
    try:
        result = await provider.authenticate(use_device_flow=True)
        if result.success:
            print("✓ OAuth authentication successful!")
            print(f"Access Token: {result.access_token[:20]}...")
            print(f"Has refresh token: {result.refresh_token is not None}")
            if result.expires_at:
                print(f"Expires at: {result.expires_at}")
            
            # Test that credentials are properly stored
            cred_manager = CredentialManager()
            stored_creds = cred_manager.load_credentials("qwen_oauth")
            if stored_creds:
                print("✓ Credentials stored successfully!")
                print(f"Stored access token: {stored_creds.access_token[:20]}...")
                print(f"Stored expires_at: {stored_creds.expires_at}")
                
                # Test that JSON file is also created
                json_path = Path.home() / ".qwen" / "oauth_creds.json"
                if json_path.exists():
                    with open(json_path, 'r') as f:
                        json_data = json.load(f)
                    print("✓ JSON file created successfully!")
                    print(f"JSON access token: {json_data.get('access_token', '')[:20] if json_data.get('access_token') else 'None'}")
                    print(f"JSON expires_at: {json_data.get('expires_at')}")
                else:
                    print("✗ JSON file not created")
            else:
                print("✗ Credentials not stored properly")
        else:
            print(f"✗ OAuth authentication failed: {result.error_message}")
    except Exception as e:
        print(f"✗ OAuth authentication error: {str(e)}")
        import traceback
        traceback.print_exc()

def test_ai_client_with_oauth():
    """Test AI client with OAuth token."""
    print("\nTesting AI client with OAuth token...")
    
    # Load credentials
    cred_manager = CredentialManager()
    credentials = cred_manager.load_credentials("qwen_oauth")
    
    if credentials and credentials.access_token:
        print("✓ Found OAuth credentials")
        
        # Create AI client with OAuth token
        ai_client = QwenClient(
            api_key=credentials.access_token,
            is_oauth_token=True
        )
        
        print(f"Base URL: {ai_client.base_url}")
        print(f"Is OAuth token: {ai_client.is_oauth_token}")
        print("✓ AI client created successfully!")
    else:
        print("✗ No OAuth credentials found")

if __name__ == "__main__":
    # Run OAuth flow test
    asyncio.run(test_oauth_flow())
    
    # Test AI client
    test_ai_client_with_oauth()