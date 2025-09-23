#!/usr/bin/env python3
"""
Debug script to test different Authorization header formats with DashScope
"""

import asyncio
import aiohttp
from qwen_code.auth.credentials import CredentialManager

async def test_different_auth_formats():
    """Test different Authorization header formats to see which one works."""
    print("Testing different Authorization header formats...")
    
    # Load credentials
    cred_manager = CredentialManager()
    credentials = cred_manager.load_credentials("qwen_oauth")
    
    if not credentials or not credentials.access_token:
        print("[FAIL] No OAuth credentials found")
        return
    
    access_token = credentials.access_token
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    print(f"Access token length: {len(access_token)}")
    print(f"Access token preview: {access_token[:50]}...")
    
    # Test different formats
    formats_to_test = [
        ("Bearer token", f"Bearer {access_token}"),
        ("Just token", access_token),
        ("Bearer sk-", f"Bearer sk-{access_token}"),  # Try with sk- prefix
        ("sk- prefix", f"sk-{access_token}"),  # Try with sk- prefix only
    ]
    
    for format_name, auth_header in formats_to_test:
        print(f"\nTesting format: {format_name}")
        print(f"Auth header preview: {auth_header[:60]}...")
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": auth_header,
                    "Content-Type": "application/json"
                }
                
                # Make a simple request to test authentication
                async with session.get(
                    f"{base_url}/models",
                    headers=headers
                ) as response:
                    print(f"Response status: {response.status}")
                    if response.status == 200:
                        print("[SUCCESS] This format works!")
                        response_data = await response.json()
                        print(f"Response data preview: {str(response_data)[:100]}...")
                        break
                    elif response.status == 401:
                        error_text = await response.text()
                        print(f"Error response: {error_text[:100]}...")
                    else:
                        print(f"Other status code: {response.status}")
                        
        except Exception as e:
            print(f"Exception during request: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_different_auth_formats())