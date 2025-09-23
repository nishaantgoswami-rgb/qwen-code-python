#!/usr/bin/env python3
"""
Debug script for OAuth authentication
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from qwen_code.auth.providers import QwenOAuthProvider


async def test_oauth():
    """Test OAuth functionality"""
    print("Testing Qwen OAuth...")
    
    # Create OAuth provider
    provider = QwenOAuthProvider(
        client_id="f0304373b74a44d2b584a3fb70ca9e56",
        redirect_uri="http://localhost:8080/callback"
    )
    
    print(f"Provider created: {type(provider)}")
    
    # Test device code flow
    try:
        print("Getting device code...")
        device_response = await provider.get_device_code()
        print(f"Device code response: {device_response}")
    except Exception as e:
        print(f"Error getting device code: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_oauth())