#!/usr/bin/env python3
"""
Test different approaches to using OAuth tokens with Qwen API
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_different_approaches():
    """Test different approaches to using OAuth tokens."""
    print("Testing different approaches to using OAuth tokens...")
    
    # Load credentials
    with open('C:\\Users\\nisha\\.qwen\\oauth_creds.json', 'r') as f:
        data = json.load(f)
    
    access_token = data.get('access_token')
    print(f"Using access token: {access_token[:30]}...")
    
    # Test different base URLs and headers combinations
    test_cases = [
        {
            "name": "DashScope compatible mode with QWEN_OAUTH header",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "headers": {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-DashScope-AuthType": "QWEN_OAUTH"
            }
        },
        {
            "name": "DashScope compatible mode with QWEN_OAUTH header and cache control",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "headers": {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-DashScope-AuthType": "QWEN_OAUTH",
                "X-DashScope-CacheControl": "enable"
            }
        },
        {
            "name": "DashScope API v1 directly",
            "base_url": "https://dashscope.aliyuncs.com/api/v1",
            "headers": {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        },
        {
            "name": "Qwen chat API directly",
            "base_url": "https://chat.qwen.ai/api/v1",
            "headers": {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        }
    ]
    
    payload = {
        "model": "qwen3-coder-plus",
        "messages": [
            {
                "role": "user",
                "content": "Hello, this is a test message."
            }
        ],
        "stream": False
    }
    
    for i, test_case in enumerate(test_cases):
        print(f"\n--- Test {i+1}: {test_case['name']} ---")
        endpoint = f"{test_case['base_url']}/chat/completions"
        
        print(f"Request URL: {endpoint}")
        print(f"Request headers: {test_case['headers']}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, headers=test_case['headers'], json=payload) as response:
                    print(f"Response status: {response.status}")
                    if response.status == 200:
                        response_data = await response.json()
                        print(f"Success! Response: {json.dumps(response_data, indent=2)}")
                        return  # If one works, we're done
                    else:
                        error_text = await response.text()
                        print(f"Error: {error_text}")
                        
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_different_approaches())