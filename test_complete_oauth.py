#!/usr/bin/env python3
"""
Complete OAuth authentication test
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from qwen_code.auth.providers import QwenOAuthProvider


async def test_complete_oauth():
    """Test complete OAuth authentication flow"""
    print("Testing complete Qwen OAuth flow...")
    
    # Create OAuth provider
    provider = QwenOAuthProvider(
        client_id="f0304373b74a44d2b584a3fb70ca9e56",
        redirect_uri="http://localhost:8080/callback"
    )
    
    print(f"Provider created: {type(provider)}")
    
    # Test complete authentication flow
    try:
        print("Starting authentication...")
        auth_result = await provider.authenticate(use_device_flow=True)
        print(f"Authentication result: {auth_result}")
        
        if auth_result.success:
            print("Authentication successful!")
            print(f"Access token: {auth_result.access_token[:20]}...")
        else:
            print(f"Authentication failed: {auth_result.error_message}")
            
    except Exception as e:
        print(f"Error during authentication: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_complete_oauth())