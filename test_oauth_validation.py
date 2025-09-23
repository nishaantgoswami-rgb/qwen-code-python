#!/usr/bin/env python3
"""
Test OAuth token validation endpoints
"""

import asyncio
import aiohttp
import json

async def test_oauth_validation():
    """Test OAuth token validation endpoints."""
    print("Testing OAuth token validation endpoints...")
    
    # Load credentials
    with open('C:\\\\Users\\\\nisha\\\\.qwen\\\\oauth_creds.json', 'r') as f:
        data = json.load(f)
    
    access_token = data.get('access_token')
    print(f"Using access token: {access_token[:30]}...")
    
    # Test different validation endpoints
    test_endpoints = [
        "https://dashscope.aliyuncs.com/api/v1/user",
        "https://chat.qwen.ai/api/v1/user",
        "https://dashscope.aliyuncs.com/api/v1/user/info",
        "https://chat.qwen.ai/api/v1/user/info",
        "https://dashscope.aliyuncs.com/compatible-mode/v1/user",
        "https://chat.qwen.ai/api/v1/oauth2/userinfo",
        "https://dashscope.aliyuncs.com/api/v1/oauth2/userinfo"
    ]
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    for endpoint in test_endpoints:
        print(f"\\nTesting endpoint: {endpoint}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, headers=headers) as response:
                    print(f"Response status: {response.status}")
                    if response.status == 200:
                        try:
                            response_data = await response.json()
                            print(f"Success! Response: {json.dumps(response_data, indent=2)}")
                        except:
                            response_text = await response.text()
                            print(f"Success! Response (text): {response_text[:200]}...")
                    elif response.status == 401:
                        error_text = await response.text()
                        print(f"Unauthorized: {error_text[:100]}...")
                    elif response.status == 404:
                        print("Endpoint not found")
                    else:
                        print(f"Other status: {response.status}")
                        try:
                            error_text = await response.text()
                            print(f"Response: {error_text[:100]}...")
                        except:
                            pass
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_oauth_validation())